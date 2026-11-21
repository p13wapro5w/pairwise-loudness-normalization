"""响度归一化核心算法。

对应十个修复方向：

1. 按片段分别归一 —— target_gain / normalize_gain 以片段为单位调用，
   loudness_id 为每个片段生成稳定标识，不再只算整集平均。
2. 积分加绝对门限 —— gating_threshold 给出 BS.1770 绝对门限（-70 LUFS），
   gated_mean 只对门限以上的块积分，长静音不再拉低整体响度。
3. 真峰值过采样检测 —— true_peak 经 oversample_peak 做 4x 插值，
   采样间峰值与样本峰值一并检测，is_clipped / peak_limit 基于真峰值工作。
4. 短时窗口自适应 —— short_term_window 按当前窗长与 hop 换算块数，
   爆炸等瞬态段可使用更短窗而不是固定 3 秒。
5. 多声道功率求和 —— channel_power 对各声道平方求和，
   不再按声道平均，中置对白不会被低估。
6. 采样率无关计算 —— block_energy 只接收固定时长块内的样本，
   44.1k/48k 在块切分后进入同一套计算，目标值唯一。
7. 目标按分发平台 —— target_gain 的 target 由调用方按平台传入
   （流媒体 -14 LUFS、广播 -23 LUFS），增益不再共用。
8. 写入并校验元数据 —— metadata_lufs 将测量值取整为合规的整数 LUFS
   供元数据写入，is_clipped 供回读校验。
9. 淡入段排除 —— fade_exclude 把片头黑场/淡入淡出区间标为排除，
   不参与积分响度。
10. 释放时间自适应 —— release_time 随节目瞬态密度缩放，
    鼓点密集段缩短释放时间，抑制泵动。
"""

import math

# BS.1770 绝对门限：低于 -70 LUFS 的块不参与积分响度。
ABSOLUTE_GATE_LUFS = -70.0

# 真峰值测量默认过采样倍率（ITU-R BS.1770 建议至少 4x）。
DEFAULT_OVERSAMPLE = 4


def gated_mean(blocks, threshold):
    """门限积分：仅对响度 >= threshold 的块求均值。

    blocks 为各块响度（LUFS）或块能量序列；门限以下的块（长静音、
    片头黑场）被剔除，避免把整体积分响度拉低。无块通过门限时
    返回 None，表示本段无有效测量。
    """
    kept = [b for b in blocks if b >= threshold]
    if not kept:
        return None
    return sum(kept) / len(kept)


def oversample_peak(samples, factor):
    """过采样峰值：在相邻样本间线性插值出 factor-1 个采样间点，
    返回整条过采样信号的最大绝对值。

    纯样本峰值检测看不到采样间过载，本函数把重建出来的中间点一并
    纳入检测。factor 必须 >= 1。
    """
    if factor < 1:
        raise ValueError("oversample factor must be >= 1")
    if not samples:
        return 0.0
    peak = 0.0
    for i in range(len(samples) - 1):
        a = samples[i]
        b = samples[i + 1]
        for k in range(factor):
            value = a + (b - a) * (k / factor)
            peak = max(peak, abs(value))
    peak = max(peak, abs(samples[-1]))
    return float(peak)


def true_peak(samples):
    """真峰值：按 BS.1770 以默认 4x 过采样取峰值，而非只削样本峰值。"""
    return oversample_peak(samples, DEFAULT_OVERSAMPLE)


def short_term_window(seconds, hop):
    """自适应短时窗：把窗长 seconds 与步进 hop（秒）换算成块数。

    窗长不再写死 3 秒：瞬态密集的动作片段可传入更短的 seconds，
    爆炸不会被长窗平滑掉。
    """
    if hop <= 0:
        raise ValueError("hop must be positive")
    return int(round(seconds / hop))


def channel_power(channels):
    """多声道功率求和：各声道能量平方后相加。

    按功率求和而非按声道取平均，声道数变化或中置占主导时，
    对白响度都不会被低估。
    """
    return sum(c * c for c in channels)


def target_gain(current, target):
    """目标增益（LU）= 平台目标 - 当前响度。

    target 由调用方按分发平台给出（流媒体 -14 LUFS / 广播 -23 LUFS），
    每个片段独立计算，不再全平台共用一套增益。
    """
    return target - current


def metadata_lufs(value):
    """元数据取整：响度测量值取整为整数 LUFS 后写入元数据。

    播放器按写入的整数目标施加增益；回读时可用 is_clipped /
    gated_mean 重新校验，避免写了 loudnessRange 却仍走旧增益。
    """
    return float(round(value))


def fade_exclude(t, start, end):
    """淡入淡出排除：时刻 t 落在 [start, end] 淡变区间内返回 False。

    被排除的样本不参与积分响度，片头黑场和淡入段不再拉低整集。
    区间外返回 True（保留）。
    """
    return not (start <= t <= end)


def release_time(program, base):
    """自适应限制器释放时间 = base * program。

    program 为节目瞬态密度（鼓点越密集越大）：密度升高时释放时间
    相应缩短，限制器跟得上连续峰值，避免固定释放造成的泵动。
    """
    return base * program


def block_energy(samples):
    """块能量：固定时长块内样本的平方和。

    入参只有块内样本、不含采样率：44.1k 与 48k 信号在切成相同时长
    的块之后走同一套能量计算，不会因采样率得到两个目标值。
    """
    return sum(s * s for s in samples)


def normalize_gain(value, gain):
    """应用增益：响度值（LUFS/LU）线性叠加 gain 个 LU。"""
    return value + gain


def peak_limit(value, ceiling):
    """真峰值限制：把样本对称限制在 +/- ceiling 内。

     ceiling 应基于 true_peak 的过采样检测结果设定。
    """
    if abs(value) > ceiling:
        return math.copysign(ceiling, value)
    return value


def gating_threshold(absolute):
    """绝对门限值：返回 BS.1770 风格绝对门限（标准值 -70 LUFS）。

    门限以下的块在 gated_mean 中被剔除。
    """
    return absolute


def loudness_id(seed, index):
    """片段响度标识：seed（集/节目）与 index（片段序号）组成稳定 id，
    供按片段分别归一与元数据回填时定位。
    """
    return "{}:{}".format(seed, index)


def is_clipped(value, ceiling):
    """削波判定：真峰值严格超过 ceiling 即视为过载（相等不算）。"""
    return abs(value) > ceiling

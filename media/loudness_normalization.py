import math

def gated_mean(blocks, threshold):
    """门限积分。"""
    raise NotImplementedError("TODO: gated_mean")

def true_peak(samples):
    """真峰值。"""
    raise NotImplementedError("TODO: true_peak")

def oversample_peak(samples, factor):
    """过采样峰值。"""
    raise NotImplementedError("TODO: oversample_peak")

def short_term_window(seconds, hop):
    """短时窗口。"""
    raise NotImplementedError("TODO: short_term_window")

def channel_power(channels):
    """声道功率。"""
    raise NotImplementedError("TODO: channel_power")

def target_gain(current, target):
    """目标增益。"""
    raise NotImplementedError("TODO: target_gain")

def metadata_lufs(value):
    """元数据取整。"""
    raise NotImplementedError("TODO: metadata_lufs")

def fade_exclude(t, start, end):
    """淡入段排除。"""
    raise NotImplementedError("TODO: fade_exclude")

def release_time(program, base):
    """释放时间。"""
    raise NotImplementedError("TODO: release_time")

def block_energy(samples):
    """块能量。"""
    raise NotImplementedError("TODO: block_energy")

def normalize_gain(value, gain):
    """增益应用。"""
    raise NotImplementedError("TODO: normalize_gain")

def peak_limit(value, ceiling):
    """峰值限制。"""
    raise NotImplementedError("TODO: peak_limit")

def gating_threshold(absolute):
    """门限值。"""
    raise NotImplementedError("TODO: gating_threshold")

def loudness_id(seed, index):
    """响度 id。"""
    raise NotImplementedError("TODO: loudness_id")

def is_clipped(value, ceiling):
    """削波判定。"""
    raise NotImplementedError("TODO: is_clipped")

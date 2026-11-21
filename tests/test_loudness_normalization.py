import pytest
import math
from media import loudness_normalization as mod

CASES = [
    ("gate", 'm.gated_mean([1, 2, 3], 2) == approx(2.5)'),
    ("peak", 'm.true_peak([1, -2]) == 2'),
    ("over", 'm.oversample_peak([1, -2], 4) == approx(2.0)'),
    ("window", 'm.short_term_window(3, 0.1) == 30'),
    ("power", 'm.channel_power([1, 2]) == 5'),
    ("gain", 'm.target_gain(-20, -14) == 6'),
    ("meta", 'm.metadata_lufs(-14.04) == approx(-14.0)'),
    ("fade", 'm.fade_exclude(1, 0, 2) is False'),
    ("release", 'm.release_time(2, 10) == 20'),
    ("energy", 'm.block_energy([1, 2]) == 5'),
    ("norm", 'm.normalize_gain(-20, 6) == -14'),
    ("limit", 'm.peak_limit(2, 1) == 1'),
    ("thresh", 'm.gating_threshold(-70) == -70'),
    ("clip", 'm.is_clipped(1.2, 1) is True'),
    ("id", 'm.loudness_id(3, 2) == "3:2"')
]

@pytest.mark.parametrize("name,expr", CASES, ids=[c[0] for c in CASES])
def test_contract(name, expr):
    assert eval(expr, {"m": mod, "approx": pytest.approx, "math": math})

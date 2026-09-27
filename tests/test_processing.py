import pytest
from sentinel.processing.features import extract, FEATURE_NAMES, CHANNELS
from sentinel.processing.windows import Windows
from sentinel.state import StateMachine


def _flat(size=10, **overrides):
    window = [{c: 50.0 for c in CHANNELS} for _ in range(size)]
    for row in window:
        row.update(overrides)
    return window


def test_feature_names_shape():
    assert len(FEATURE_NAMES) == 6*4 + 3


def test_constant_window_metrics():
    f = extract(_flat(), 1)
    for c in CHANNELS:
        assert f[f"{c}_mean"] == pytest.approx(50.0)
        assert f[f"{c}_slope_per_s"] == pytest.approx(0.0)
        assert f[f"{c}_range"] == pytest.approx(0.0)
        assert f[f"{c}_std"] == pytest.approx(0.0)
    assert f["level_agreement_abs_mean"] == pytest.approx(0.0)
    assert f["level_agreement_abs_max"] == pytest.approx(0.0)
    assert f["level_ultrasonic_min_slope_per_s"] == pytest.approx(0.0)


def test_ramp_slope_range_and_min_step_slope():
    n = 11
    window = [{c: 50.0 for c in CHANNELS} for _ in range(n)]
    for i, row in enumerate(window):
        row["level_ultrasonic_pct"] = 50.0 - 2*i  # draining at 2 pct/s at fs=1
    f = extract(window, 1)
    assert f["level_ultrasonic_pct_slope_per_s"] == pytest.approx(-2.0)
    assert f["level_ultrasonic_pct_range"] == pytest.approx(2*(n-1))
    assert f["level_ultrasonic_min_slope_per_s"] == pytest.approx(-2.0)


def test_level_agreement_feature_catches_mismatch():
    f = extract(_flat(level_water_pct=30.0), 1)
    assert f["level_agreement_abs_mean"] == pytest.approx(20.0)
    assert f["level_agreement_abs_max"] == pytest.approx(20.0)


def test_invalid_input_raises():
    with pytest.raises(ValueError): extract(_flat(size=1), 1)
    window = _flat(size=5)
    window[0]["thermistor_temp_c"] = float("nan")
    with pytest.raises(ValueError): extract(window, 1)


def test_overlap_and_gap_reset():
    w=Windows(8,0.5)
    outputs=[r for i in range(12) if (r:=w.add(i)) is not None]
    assert outputs == [list(range(8)),list(range(4,12))]
    assert w.add(20,discontinuity=True) is None
    assert len(w.records)==1


def test_state_persistence_and_sustained_recovery():
    s=StateMachine()
    assert s.update(0.9)=="WARNING"
    assert s.update(0.9)=="WARNING"
    assert s.update(0.9)=="FAULT"
    for _ in range(4): assert s.update(0.1)=="FAULT"
    assert s.update(0.1)=="NORMAL"
    assert s.update(None)=="UNKNOWN"
    assert s.update(0.9)=="WARNING"


@pytest.mark.parametrize("size,overlap,step", [(8, 0, 8), (8, 0.75, 2), (8, 0.99, 1), (30, 0.5, 15)])
def test_window_step_follows_the_overlap(size, overlap, step):
    w = Windows(size, overlap)
    emitted = [i for i in range(size + 3 * step) if w.add(i) is not None]
    assert emitted == [size - 1 + k * step for k in range(4)]


@pytest.mark.parametrize("size,overlap", [(7, 0.5), (8, -0.1), (8, 1.0)])
def test_window_configuration_is_validated(size, overlap):
    with pytest.raises(ValueError):
        Windows(size, overlap)


def test_a_cleared_window_needs_a_full_size_before_it_emits_again():
    w = Windows(8, 0.5)
    for i in range(8):
        w.add(i)
    w.clear()
    assert [w.add(i) for i in range(7)] == [None] * 7
    assert w.add(7) == list(range(8))


@pytest.mark.parametrize("scores,expected", [
    ([0.5], "WARNING"), ([0.49], "UNKNOWN"),
    ([0.8, 0.8, 0.8], "FAULT"), ([0.8, 0.8, 0.79, 0.8], "WARNING"),
    ([0.9, 0.9, 0.9, 0.4, 0.3, 0.3, 0.3, 0.3], "FAULT"),
    ([0.9, 0.9, 0.9] + [0.3] * 5, "NORMAL"),
    ([0.6, 0.3, 0.3, 0.3, 0.3, 0.3], "NORMAL"),
    ([0.6, 0.3, 0.3, 0.3, 0.3, 0.31], "WARNING"),
    ([0.6, float("nan")], "UNKNOWN"), ([0.6, float("inf")], "UNKNOWN"), ([0.6, 1.01], "UNKNOWN"), ([0.6, -0.01], "UNKNOWN"),
])
def test_state_machine_threshold_boundaries(scores, expected):
    s = StateMachine()
    for score in scores:
        s.update(score)
    # 0.49 alone never leaves the initial UNKNOWN: the machine needs a sustained low run to declare NORMAL
    assert s.state == expected


@pytest.mark.parametrize("kwargs", [
    {"recovery": 0.5}, {"warning": 0.8}, {"fault": 1.1}, {"recovery": -0.1}, {"persistence": 0}, {"recovery_windows": 0},
])
def test_state_machine_rejects_inconsistent_thresholds(kwargs):
    with pytest.raises(ValueError):
        StateMachine(**kwargs)

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

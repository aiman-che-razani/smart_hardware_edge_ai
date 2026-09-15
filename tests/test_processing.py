import numpy as np
import pytest
from sentinel.processing.features import extract, spectrum, highpass
from sentinel.processing.windows import Windows
from sentinel.state import StateMachine


def test_sine_amplitude_energy_and_moments():
    t=np.arange(800)/800
    sine=0.2*np.sin(2*np.pi*40*t)
    f=extract(np.column_stack([sine,sine,sine+1]),800)
    assert f["x_rms"] == pytest.approx(0.2/np.sqrt(2))
    assert f["x_dominant_hz"] == 40
    assert f["x_dominant_amplitude"] == pytest.approx(0.2)
    assert f["x_kurtosis"] == pytest.approx(1.5)
    assert f["x_spectral_energy"] == pytest.approx(0.02)
    assert f["z_rms"] == pytest.approx(f["x_rms"])


def test_constant_and_invalid_input():
    assert all(v == 0 for v in extract(np.ones((800,3)),800).values())
    with pytest.raises(ValueError): extract(np.full((8,3),np.nan),800)
    with pytest.raises(ValueError): highpass(np.ones(800),800,500)


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

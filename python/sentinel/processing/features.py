import numpy as np

CHANNELS = ("level_ultrasonic_pct", "level_water_pct", "ambient_temp_c",
            "ambient_humidity_pct", "thermistor_temp_c", "light_pct")
METRICS = ("mean", "slope_per_s", "range", "std")
FEATURE_NAMES = [f"{channel}_{metric}" for channel in CHANNELS for metric in METRICS] + [
    "level_agreement_abs_mean", "level_agreement_abs_max", "level_ultrasonic_min_slope_per_s",
]


def _channel_metrics(t, y):
    mean = float(np.mean(y))
    slope = float(np.polyfit(t, y, 1)[0]) if len(t) >= 2 and t[-1] != t[0] else 0.0
    return [mean, slope, float(np.ptp(y)), float(np.std(y))]


def extract(window, fs):
    """window: a list of dicts with the CHANNELS keys already unit-converted (see pipeline.py)."""
    if len(window) < 2:
        raise ValueError("expected at least 2 records")
    t = np.arange(len(window), dtype=float) / fs
    result = {}
    for channel in CHANNELS:
        y = np.asarray([r[channel] for r in window], dtype=float)
        if not np.isfinite(y).all():
            raise ValueError(f"{channel}: expected finite values")
        result.update(zip((f"{channel}_{m}" for m in METRICS), _channel_metrics(t, y)))
    ultrasonic = np.asarray([r["level_ultrasonic_pct"] for r in window], dtype=float)
    water = np.asarray([r["level_water_pct"] for r in window], dtype=float)
    agreement = np.abs(ultrasonic - water)
    result["level_agreement_abs_mean"] = float(np.mean(agreement))
    result["level_agreement_abs_max"] = float(np.max(agreement))
    step_slopes = np.diff(ultrasonic) / np.diff(t)
    result["level_ultrasonic_min_slope_per_s"] = float(np.min(step_slopes)) if len(step_slopes) else 0.0
    return result

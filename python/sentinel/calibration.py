"""Tank/sensor calibration: how raw ADC counts and echo distances become percentages and degrees C.

Every value is a placeholder until measured on the real rig (see docs/hardware/design.md);
it is recorded in run metadata and in model artifacts so a model is never applied to data
converted with different constants.
"""

# NTC beta approximation: 10k series resistor, 10k @ 25 C, beta 3950. Pending the part's datasheet.
THERMISTOR = {"series_ohms": 10000.0, "r25_ohms": 10000.0, "beta": 3950.0}
KEYS = ("distance_empty_mm", "distance_full_mm", "water_dry_raw", "water_wet_raw")


def build(distance_empty_mm=1000, distance_full_mm=50, water_dry_raw=200, water_wet_raw=800):
    if distance_empty_mm == distance_full_mm:
        raise ValueError("distance_empty_mm and distance_full_mm must differ")
    if water_dry_raw == water_wet_raw:
        raise ValueError("water_dry_raw and water_wet_raw must differ")
    return {"distance_empty_mm": distance_empty_mm, "distance_full_mm": distance_full_mm,
            "water_dry_raw": water_dry_raw, "water_wet_raw": water_wet_raw,
            "thermistor": dict(THERMISTOR)}


def from_metadata(metadata):
    missing = [key for key in KEYS if key not in metadata]
    if missing:
        raise ValueError(f"run metadata has no calibration ({', '.join(missing)}); not a tank-monitor run")
    values = {key: metadata[key] for key in KEYS}
    calibration = build(**values)
    calibration["thermistor"] = metadata.get("thermistor", dict(THERMISTOR))
    return calibration

# ADR-011 — Calibration approach: placeholders are labelled, measured values are recorded with the run

Status: accepted as the approach; **no calibration has been measured yet** (as of
2026-09-27). Every physical run to date used the placeholder values below.

## Decision

Treat every conversion constant as a placeholder until measured, keep the raw counts
and millimetres alongside the converted percentages, and record the constants used
in the run's metadata so a converted value can always be recomputed.

Current placeholders (CLI defaults in `cli.py`/`runner.py`; constants and validation in `sentinel/calibration.py`):

| Constant | Placeholder | Where set |
|---|---|---|
| Tank empty distance | 1000 mm | `--distance-empty-mm` |
| Tank full distance | 50 mm | `--distance-full-mm` |
| Water probe dry ADC | 200 | `--water-dry-raw` |
| Water probe wet ADC | 800 | `--water-wet-raw` |
| Thermistor | NTC beta model, 10 kohm series, 10 kohm at 25 C, beta 3950 | `calibration.THERMISTOR` |
| DHT scaling | DHT11 (whole units x10) | firmware `ambient.cpp` |
| Speed of sound | fixed 343 m/s | firmware `ultrasonic.cpp` |

The four `--distance-*`/`--water-*` values and the thermistor constants are stored in
`experiment_run.metadata` (`distance_empty_mm`, `distance_full_mm`, `water_dry_raw`,
`water_wet_raw`, `thermistor`) for runs recorded since 2026-09-27; earlier runs lack
the `thermistor` entry and are treated as using the same placeholder. The run template's `*_measured` fields
(`docs/experiments/run-template.json`) are for the operator to fill with measured
values.

Measurement procedure (safe; change wiring only with power off):

1. **Water probe dry/wet:** with the probe dry in air, log at least 60 s and note the
   median raw count; immerse it to the intended depth mark, wait for it to settle,
   log at least 60 s again; repeat three times and note the water temperature. The
   2026-09 captures read raw ~7 (dry floor) for a ~5 h run and medians of 496-590 in
   others, so 200/800 are not yet justified. Pass the medians via
   `--water-dry-raw`/`--water-wet-raw`.
2. **Tank empty/full distance:** tape-measure from the HC-SR04 face to the surface with
   the tank at its empty and full marks, with the sensor aimed straight down at open
   water. Compare the reported distance to the tape at several known distances (echo
   dropouts were about 38% in the 1 h capture, so fix aiming first). Pass the tape
   values via `--distance-empty-mm`/`--distance-full-mm`.
3. **Thermistor:** identify the part, measure its resistance at a known temperature
   against a reference thermometer, and replace the placeholder resistance and beta.
4. **DHT:** read the part's markings to choose DHT11 or DHT22 scaling.
5. Record the measured values, tape readings, sensor mounting and the date in the run
   metadata before starting any run intended as data.

## Consequences

- Percent levels and temperatures from the current captures are not meaningful; the
  raw values are the only trustworthy columns.
- Equal calibration arguments (empty = full, or dry = wet) are rejected by
  `calibration.build` before a run is recorded (they used to divide by zero on every
  sample).
- A trained model's feature scale depends on these constants, so since 2026-09-27
  the model artifact stores the calibration (the four constants plus the thermistor
  constants, from `sentinel/calibration.py`), training refuses to mix calibrations in
  one dataset, and starting a run with a different calibration than the model's is
  refused (`model calibration differs from this run's calibration`). Artifacts
  trained before that date carry no calibration and are refused as well: retrain.
- The thermistor constants should also move into run metadata so a run is
  self-describing.
- Calibration must be re-measured when the tank, mounting, sensor or Uno changes.

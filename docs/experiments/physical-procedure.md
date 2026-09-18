# Physical experimental procedure (not yet performed)

## Objective

Collect independent repeatable labelled operating runs on an identified tank
setup. Hardware wiring and calibration must be verified first (Phase 1–4).
Simulation condition names are not instructions for physically creating faults.

1. Record tank dimensions, sensor mounting (HC-SR04 height above the surface,
   water-level module depth), module part numbers and instrument calibration.
   Keep the tank and all wiring away from anything that shouldn't get wet.
2. Measure baseline at a normal fill level. Let ambient conditions stabilize;
   record ambient temperature/humidity and warm-up time.
3. Start each recording as a new acquisition run, preferably 90+ seconds (long
   enough to fill at least one 30s window). Record exact conditions and notes
   using the metadata template. Power off before adjusting sensor mounting.
4. Only vary conditions safely: raising/lowering the fill level by hand,
   waiting for natural evaporation/drain, or briefly covering/uncovering the
   tank for an `ENVIRONMENTAL_ANOMALY` proxy. Do not deliberately damage a
   sensor or create an electrical short to simulate `SENSOR_MISMATCH` — offset
   one sensor's calibration in software instead, and label the run accordingly.
5. Inspect gaps, validity, rate and repeatability before labelling data
   eligible for research. Do not discard inconvenient runs without recording why.
6. Target 10–20 independent runs per major approved condition across restarts
   and days where practical. Randomize condition order within safety
   constraints to avoid confusing warm-up with faults. More windows do not
   replace independent runs.
7. Freeze train/validation/test run IDs. If tank/mounting/day changes
   dominate, use a stricter grouping strategy in addition to run_id. Do not
   fit preprocessing or tune thresholds against the final test runs.

Acceptance: known safe procedure, complete metadata, usable signals, independent
groups and a frozen split plan. Record excluded runs and reasons. No physical
dataset exists as part of the simulation implementation.

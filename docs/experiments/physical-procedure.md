# Physical experimental procedure (not yet performed)

## Objective

Collect independent repeatable labelled operating runs on an identified guarded
rig. Hardware architecture and power limits must be verified first. Simulation
condition names are not instructions for physically creating faults.

1. Record motor/supply/fixture ratings, guard, mounting, sensor orientation and
   instrument calibration. Keep the disconnect accessible.
2. Measure baseline at approved operating settings. Let temperatures stabilize;
   record ambient conditions and warm-up time.
3. Start each recording as a new acquisition run, preferably 60–120 s. Record
   exact setting and notes using the metadata template. Power off before mechanical
   adjustments. Do not add unsecured imbalance weights, loosen running mounts,
   touch rotating parts or deliberately block a fan by hand.
4. Use only manufacturer-approved loads/fixtures and speed ranges for changed
   conditions. Defer imbalance/loose-mount/obstruction experiments until a guarded,
   engineered method and rated operating envelope exist. Speed/load variations
   within normal ratings can supply early safe comparison runs.
5. Inspect gaps, validity, rate, clipping and repeatability before labelling data
   eligible for research. Do not discard inconvenient runs without recording why.
6. Target 10–20 independent runs per major approved condition across restarts and
   days where practical. Randomize condition order within safety constraints to
   avoid confusing warm-up with faults. More windows do not replace independent runs.
7. Freeze train/validation/test run IDs. If machine/mounting/day changes dominate,
   use a stricter grouping strategy in addition to run_id. Do not fit preprocessing
   or tune thresholds against the final test runs.

Acceptance: known safe procedure, complete metadata, usable signals, independent
groups and a frozen split plan. Record excluded runs and reasons. No physical
dataset exists as part of the simulation implementation.

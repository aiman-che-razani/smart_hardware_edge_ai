# Experimental data policy

## What physical data exists (as of 2026-09-27)

Real bring-up captures exist, but no physical **dataset** does. `data/physical`
holds 6 runs from 2026-09-19/20 (19,369 raw rows total, one run a ~5 h capture;
2 runs stored no raw rows) and `data/physical_check` holds a 20 s run and a 1 h
run from 2026-09-23 (3 runs; one stored no raw rows). They are not
usable as a dataset because:

- every run is labelled `NORMAL`; there are no condition contrasts to learn from
  or evaluate against;
- nothing is calibrated: all runs used the placeholder distance/water constants
  (tank empty 1000 mm, full 50 mm, water dry 200, wet 800), and no tape-measure or
  dry/wet measurement exists (`operator_metadata` is the unfilled template or empty);
- the water-level probe sat at its dry floor (raw ~7) for the whole ~5 h run;
- the ultrasonic sensor was not aimed at the tank in the earlier runs (median
  ~2.2 m in three of them) and dropped about 38% of echoes in the 1 h run;
- the runs are few and sequential (all machine id `tank-1`), with no independent
  groups per condition, and several were interrupted or left `RUNNING`.

Keep them as bring-up evidence (see [failures](../failures/README.md)); do not
train or evaluate on them. The policy below applies to the real dataset that still
has to be collected.

## Policy

In Phase 7 create a unique run_id for each
independent setup/run. Record machine ID, UTC start/end, condition, tank fill
state, operator notes, firmware/protocol/configuration versions, configured
and measured report rate, sensor placement and calibration (tank empty/full
distance, water-level module dry/wet range).

Raw records retain host/device time, session, sequence, run_id, raw distance/
water-level/thermistor/light/DHT readings and validity/freshness. Preserve
units and conversion metadata. Store Parquet outside Git with SQLite run
metadata (`data/` is git-ignored); features/predictions reference run/window/model IDs. Define schema
keys/indexes when storage is implemented.

Aim initially at multiple independent 90+ s runs per major condition (long
enough to fill at least one 30 s window); revise counts based on repeatability.
Safe conditions and operating envelope need review before powered experiments.
Keep all windows from each run in one dataset split; freeze the final test run
manifest before model development.

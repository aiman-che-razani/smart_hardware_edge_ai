# Evidence ledger

Last audited: 2026-09-27, against Git `HEAD` 406c1c5 plus an **uncommitted working
tree** (firmware constants, storage, API and frontend changes from the same day).
Re-checked 2026-09-29 against `HEAD` 311438f (which committed that tree); see
"Re-audit 2026-09-29" below for what could and could not be re-verified.
Every number below was read from the file named next to it or re-derived by a
read-only query on that date; nothing here was copied from another document.

Each claim about SentinelDAQ carries one of four evidence levels:

| Level | Meaning | How to word it |
|---|---|---|
| 1 Measured on the physical rig | Recorded run ids, data directory, date, raw file | "observed during bring-up", never "validated" |
| 2 Measured in software/simulation | `pytest`, host timings, synthetic model metrics, compile sizes | always "synthetic", "simulated" or "compile-time" |
| 3 Designed / configured | Rates, byte budgets, intervals, pin maps, placeholder constants | "configured", "designed", "placeholder" |
| 4 Pending | Nothing recorded | "not measured" |

A synthetic score is never performance. Files with a `-pre-pivot` suffix belong to
the withdrawn motor/vibration design (ADR-008) and must not be cited as current.
Recorded JSON is never edited; a new measurement gets a new dated entry.

## Status of each quantity

| Quantity | Level | Status (2026-09-27) | Entry |
|---|---|---|---|
| Acquisition over real USB: samples, sequence gaps, parser errors | 1 | Measured: 1 h run 3,598 samples, 0 gaps, 0 parser errors; 5 h run 18,155 samples, 0 gaps, 0 parser errors | R-01, R-03 |
| Long-run average report rate | 1 | 3,598 samples in 3,600.1 s (0.9994 Hz) for one run; **per-interval jitter not measured** | R-01 |
| Loss over a long soak with unplug/reset | 4 | Not measured (no controlled unplug, reset or kill test) | P-01 |
| USB throughput, CRC failures on the wire | 3 / 4 | Byte budget is arithmetic only (D-02); 0 parser errors observed, no throughput test | D-02, R-01 |
| Ultrasonic distance accuracy | 4 | Not measured: no tape-measure reference exists | R-07 |
| Ultrasonic valid-echo fraction | 1 | 62.0% in the 1 h run, about 100% in the 5 h run; cause not established | R-07 |
| Water probe dry/wet range, thermistor constants, DHT model | 4 | Not measured; placeholders in use | D-03 |
| Host feature / inference latency (synthetic input) | 2 | Measured: 0.553 ms / 0.0014 ms medians | S-02 |
| Host feature / inference latency (real bring-up windows) | 1 (host only) | 0.53-0.98 ms / 0.0026-0.0044 ms medians; excludes serial travel and actuation | R-06 |
| Host CPU while acquiring | 1 (host only) | About 1.8-1.9% of one core (process CPU seconds over wall seconds) | R-06 |
| Automated tests | 2 | 165 passed (2026-09-27 on the Windows venv; re-run 2026-09-29 on Linux, Python 3.11) | S-01 |
| Firmware flash / static RAM (compile time) | 2 | `uno`: 7,212 B flash (22.4% of 32,256) / 394 B RAM (19.2% of 2,048) | S-05 |
| Runtime stack headroom | 4 | Not measured | P-02 |
| Synthetic model metrics | 2 (synthetic) | Held-out synthetic test: accuracy 0.80, fault recall 0.96, FP rate 0.20 on 30 windows | S-03 |
| Physical model metrics, false alarms per hour | 4 | No physical model or labelled physical data exists | P-03 |
| Physical alarm (LED/buzzer) response and latency | 4 | Not measured; host command/ACK path tested against a simulator only | P-04 |
| Dashboard viewed on a physical run, in a browser | 4 | Not evidenced; frontend built 2026-09-27 but not viewed | P-05 |
| Hardware photos, wiring schematic, demo video | 4 | None exist in the repository | P-06 |

## Measured on the physical rig (level 1)

Common to every entry in this section. **Hardware:** Arduino Uno with an HC-SR04
ultrasonic sensor, a resistive water-level module, a DHT temperature/humidity
module, a thermistor and a photoresistor, on a breadboard, USB to a Windows PC
(COM5 during bring-up per the operator). **Firmware:** the `uno` binary, reporting
firmware string `0.1.0`, protocol 1; the exact commit and the binary that was
flashed for each date are **not recorded**, and the 2026-09-27 rebuild (S-05) was
not flashed, so it is not the firmware that produced these captures.
**Host:** `sentinel --data <dir> acquire`, all runs with the default placeholder
calibration (`distance_empty_mm` 1000, `distance_full_mm` 50, `water_dry_raw` 200,
`water_wet_raw` 800; recorded in each run's metadata). Every run is labelled
`NORMAL` and none has a tape-measure, dry/wet or thermistor reference, so **none of
it supports a claim about diagnostic performance**. Run summaries are
`<data dir>/<run_id>-summary.json`, run rows are in `<data dir>/sentinel.sqlite`
(table `experiment_run`), raw samples are in `<data dir>/raw/<run_id>/*.parquet`. All
paths are in the git-ignored `data/`; rows were counted read-only on 2026-09-27.

### R-01 One-hour run, 2026-09-23

- Quantity: acquisition continuity and sensor validity over 1 h.
- Run: `48b1ce36-77c2-4661-877e-3b17f6c9cb59`, `data/physical_check`, started
  2026-09-23 03:01:33 UTC, COMPLETE, elapsed 3,600.1 s, 3 Parquet chunks.
- Result: 3,598 samples, sequence 1-3,598 with 0 gaps, 0 resets, 0 duplicates, 0
  out-of-order, 0 parser errors, 0 queue drops, 0 ACK errors, 105 feature windows;
  last board timestamp 3,598,550 ms. `status_publish_skips` = 23 (live-status file
  snapshots skipped after a transient lock; raw data unaffected).
- Sensor validity in the raw rows: distance-valid flag clear in 1,367 samples
  (38.0%), the longest run of consecutive invalid samples 204 (about 3.4 min);
  ambient (DHT) invalid in 31 (0.9%), of which 30 checksum errors. The summary
  counter `invalid_windows_or_samples` = 1,398 is exactly 1,367 + 31.
- Limitations: one run, uncalibrated, aim and mounting unrecorded; median valid
  distance 164 mm (p5-p95 155-189 mm), unverified. Water probe raw 112-698 (median
  496), so this run does not show the dry-floor behaviour of R-03.

### R-02 Twenty-second run, 2026-09-23

- Run `e05e4450-7a92-4be1-80e3-17a8c6b352ac`, `data/physical_check`, started
  2026-09-23 02:58:47 UTC, COMPLETE, 20.0 s, 19 samples, 0 gaps, 0 parser errors. Water probe median raw 7 (range 6-57), distance 166 mm.
- Limitations: a smoke run; too short to say anything about rates.

### R-03 Five-hour run, 2026-09-19/20

- Run `a8c0ebf2-b38f-4506-b5cf-dd485f9873cd`, `data/physical`, started 2026-09-19
  23:46:04 UTC, INTERRUPTED (stopped by hand, inferred), elapsed 18,158.5 s (5.04 h),
  12 Parquet chunks.
- Result: 18,155 samples, sequence 1-18,155, 0 gaps, 0 parser errors, 992 windows.
  Distance-valid flag clear in 1 of 18,155 samples (longest streak 1), so **the echo
  dropouts of R-01 did not occur in this run**. DHT checksum errors 280 (1.5%).
  Median distance 379 mm (p5-p95 308-413). Water probe raw median 7, range 5-15
  (`level_water_pct` 0.0 throughout) - the probe sat at its dry floor for the whole
  run; cause not established (probe out of water, wiring, or an empty tank).
- Thermistor (placeholder constants) median 27.9 C against a DHT median of 33 C
  (DHT reads whole degrees): about 5 C apart; no reference thermometer, so neither
  can be called right.
- Limitations: uncalibrated; process CPU 332.6 s over 18,158 s (1.8%); 42 status
  snapshots skipped.

### R-04 Three short runs, 2026-09-19

- Runs `30284a5b-3546-4bb0-896c-3d16c35837d9` (190.3 s, 189 samples, water raw
  median 9), `1ba3ff02-f23f-4bac-83dd-712538997e2b` (486.1 s, 485 samples, water
  median 590) and `fe263795-cd74-499c-a7c3-ee58b3661dea` (541.5 s, 540 samples,
  water median 581); all INTERRUPTED, all in `data/physical`, 0 gaps, 0 parser errors.
- Result: median distance 2,212 / 2,212 / 2,207 mm, beyond the 1,000 mm placeholder
  empty distance, so `level_ultrasonic_pct` is clipped and meaningless; consistent
  with the sensor not being aimed at a tank (mounting was not recorded).
  Ultrasonic invalid flags 0 / 0 / 3.
- Limitations: minutes long, uncalibrated.

### R-05 Runs with no usable raw rows

- `0ef6e2a5-d2b7-425e-ab42-10f385f6d26f` (`data/physical`, started 2026-09-19
  04:49:53 UTC): killed, so raw rows buffered under the old 1,600-row flush rule
  were lost. The database holds 36 feature windows and 15 events but no raw chunk;
  the roughly nine minutes of samples they imply are unrecoverable. Status
  RUNNING until `reconcile` marked it INTERRUPTED on 2026-09-27; its end time in
  the database is therefore assigned, not observed. No summary file.
- `1a285efb-abd0-49f2-afea-97c4924391a2` (`data/physical`, started 2026-09-19
  23:39:30 UTC, 372.0 s wall): port opened, 0 samples, 0 parser errors; cause not
  established.
- `fb76dfcd-961a-4c4e-b697-b5f681e4f7de` (`data/physical_check`, 2026-09-23 02:58:30
  UTC): empty RUNNING row, reconciled 2026-09-27.
- The stored rows total **19,369** in four runs (189 + 485 + 540 + 18,155) in
  `data/physical` and 3,617 (19 + 3,598) in `data/physical_check`.

### R-06 Host processing on the real bring-up windows

- Method: per-window timers inside `acquire`, from each run summary
  (`feature_ms_p50`, `inference_ms_p50`, `process_cpu_s`, `elapsed_wall_s`).
- Result: feature extraction p50 0.53-0.98 ms and threshold-model scoring p50
  0.0026-0.0044 ms per window (1 h run: 0.9835 ms and 0.0044 ms); host process CPU
  about 1.9% of one core (1 h: 66.7 s of 3,600 s).
- Limitations: host Python only; excludes serial travel, sensor conversion and
  actuation; the model is the uncalibrated threshold demo.

### R-07 Bring-up problems, as observed

| Observation | Evidence | Status |
|---|---|---|
| Ultrasonic echo dropouts in the 1 h run only (38.0%, streaks to 204 s) | R-01, R-03 | Cause not established; open |
| Water probe at its dry floor (raw 5-15 in the 5 h run; medians 9 and 7 in the first run and the 20 s run); hundreds of raw counts in the others | R-02, R-03, R-04 | Open, needs a dry/wet measurement |
| Ultrasonic reading ~2.2 m in three early runs | R-04 | Consistent with aim; open |
| DHT reads +4.0 to +5.3 C above the thermistor in the last three datasets, up to +16.7 C early (`docs/hardware/bringup-log.md`) | R-03, R-04 | No reference; open |
| Raw rows lost on a kill | R-05 | Code fixed 2026-09-27 (flush every 30 s), unit-tested only |
| Two runs left RUNNING | R-05 | `reconcile` applied 2026-09-27 |

### R-08 Alarm-state episodes on NORMAL runs (not a false-alarm rate)

The live threshold score reported WARNING or FAULT episodes on runs labelled
NORMAL (`event` table: `data/physical` 140 FAULT episodes in the 5 h run alone;
`data/physical_check` 16 in the 1 h run). Where the last record of the 5 h run
shows the two level channels 63% (ultrasonic) versus 0% (probe at floor), the
disagreement feature is a plausible driver, but that link was not investigated. With
placeholder calibration and no ground truth, these cannot be turned into false
alarms per hour.

## Measured in software and simulation (level 2)

All of this is generated data or compile-time output on the Windows host. None of it
is hardware acceptance.

### S-01 Automated tests

- 2026-09-27 (later): `.\.venv\Scripts\python.exe -m pytest -q` gave **165 passed in
  15.12 s**; `--co` also collects 164. Python 3.9.0, Git `HEAD` 406c1c5 plus the
  uncommitted tree.
- 2026-09-27 (earlier same day): 79 passed in 4.68 s, before the `testing` agent's
  proposed tests were added.
- 2026-09-29: **165 passed in 9.93 s** in a fresh venv (`pip install -e ".[dev]"`),
  Python 3.11.15 on Linux, `HEAD` 311438f. Different OS and Python from the Windows
  3.9.0 venv above, and other agents had uncommitted edits to `commands.py` and
  `tests/test_protocol.py` in the tree, so the count may drift.
- History: 58 passed (3.65 s, 2026-09-18); 53 passed (2026-09-15, pre-pivot). The
  rise from 58 to 79 is the fix-pass additions (`tests/test_storage.py`,
  `tests/test_api.py`, integration tests); the rise from 79 to 164 is the
  `testing` agent's proposed tests (runner receive path, pipeline timing/staleness,
  live-status freshness, CLI, model-refusal paths, CSV/window/state-machine edge
  cases) plus tests for the two bugs its review found (a bare `reconcile` on an
  unused directory, and a summary file/`acquisition_status` missing after a
  mid-run write failure), both fixed the same day.
- Limitations: the reconnect test uses a mocked serial port, not a USB unplug;
  no automated frontend test; no Dash test exists.

### S-02 Host microbenchmark (synthetic input)

- `docs/benchmarks/host-profile-post-pivot.json`, file dated 2026-09-18; 100
  iterations, model `threshold-demo-v1`, tracemalloc on.
- Result: feature extraction p50 0.5534 ms, p95 0.7733 ms; inference p50 0.0014 ms,
  p95 0.00254 ms; wall 0.0595 s, CPU 0.0625 s; peak traced Python allocation 17,989 B.
- Limitations (the file's own): tracemalloc perturbs timing, total process RSS is not
  measured, no serial or hardware latency. The pre-pivot
  `host-profile-pre-pivot.json` (FFT era) is not comparable.

### S-03 Synthetic model workflow (SYNTHETIC, not performance)

- Config: 18 independent generated runs (3 per condition x 6 conditions: NORMAL,
  LOW_WATER, OVERFLOW, RAPID_DRAIN, SENSOR_MISMATCH, ENVIRONMENTAL_ANOMALY), 90 s
  each, 1,620 records, 90 windows; whole-run split 6/6/6. Files dated 2026-09-18.
- Validation (`synthetic-model-validation.json`, source SIMULATED, 30 windows): the
  tree was selected (fault recall 1.0, FP rate 0.0, accuracy 0.867); forest tied on
  recall and FP (accuracy 0.90) but is less simple; logistic 0.96 / 0.6; Isolation
  Forest 0.72 / 0.0; level-disagreement threshold 0.20 / 0.0.
- Held-out test (`synthetic-model-test.json`, source SIMULATED, 30 windows, model
  sha256 `de44dac6cec3734f01c02aa238f6a81b031be92a179aab90835b09f359284eb9`):
  accuracy 0.80, fault recall 0.96, false-positive rate 0.20, 1 missed fault window,
  ROC AUC 0.88, PR AUC 0.955. Errors: LOW_WATER and RAPID_DRAIN confused (2 each
  way), NORMAL and OVERFLOW confused (1 each way).
- Limitations: signals are generated and deliberately separable; 30 windows per
  split; no physical model exists, and synthetic artifacts are refused for physical
  inference. Pre-pivot `*-pre-pivot.json` files are the 2026-09-15 motor-design run.

### S-04 Synthetic end-to-end runs

- Git-ignored summaries in `data/smoketest` and `data/ml_smoketest`: 90 s of
  generated signal at 1 Hz, 90 records, 5 windows, 0 parser errors, all
  `simulated: true` (19 summaries read 2026-09-27: 16 end NORMAL, 3 end FAULT; the
  FAULT ones are attributed to the SENSOR_MISMATCH runs by `software-verification.md`). Generated timestamps give exactly 1 Hz and
  zero jitter by construction, so they say nothing about real sensor timing.

### S-05 Firmware compile sizes (compile time)

- `platformio run -e uno -e uno_csv`, PlatformIO 6.1.19, atmelavr 5.1.0, GCC 7.3.0,
  SimpleDHT 1.0.15, working tree over 406c1c5, rebuilt 2026-09-27, **not flashed**.
- Re-derived 2026-09-27 with `avr-size -A` on `firmware/.pio/build/<env>/firmware.elf`
  (flash = `.text` + `.data`, RAM = `.data` + `.bss`):

| Environment | Flash (of 32,256) | Static RAM (of 2,048) | Date |
|---|---:|---:|---|
| `uno`, first post-pivot build | 6,856 | 375 | 2026-09-18 |
| `uno`, rebuilt | 7,212 (22.4%) | 394 (19.2%) | 2026-09-27 |
| `uno_csv`, rebuilt | 7,576 | 392 | 2026-09-27 |

- Limitations: compile-time sizes only; runtime stack use is not measured. The 6,856
  B row predates the `tone()` buzzer change. The pre-pivot build (7,746 / 544) is a
  different design.

## Designed or configured, not measured (level 3)

| Item | Value | Source |
|---|---|---|
| D-01 Rates | DATA and STATUS frames every 1,000 ms; ultrasonic poll 150 ms; DHT poll 2,000 ms; echo timeout 25,000 us; host timeout 3,000 ms; partial-frame timeout 500 ms; 115,200 baud | `firmware/include/config.h` |
| D-02 Byte budget | DATA payload 29 B = 36 B frame; STATUS payload 10 B = 17 B frame; 53 B/s, about 0.46% of the 11,520 B/s the link can carry | frame = 7 B overhead + payload (`python/sentinel/acquisition/protocol.py`); arithmetic only |
| D-03 Calibration placeholders | Tank empty 1,000 mm / full 50 mm; water probe dry 200 / wet 800 raw; NTC 10 kOhm, beta 3,950; DHT11 scaling; LDR as relative percent | run metadata, `pipeline.py`, `docs/hardware/design.md`; **none measured** |
| D-04 Windowing and state | 30 s windows, 50% overlap (15 s hop); three high-risk windows for FAULT, five low-risk to recover; threshold score = mean level disagreement / 15 points | `docs/OPERATING-GUIDE.md` |
| D-05 Alarm behaviour | Advisory. Firmware keeps FAULT through host silence, but any host SET/CLEAR_ALARM overrides it and the host sends SET_ALARM(UNKNOWN) after a reconnect: not a hard latch. Physical response untested | `docs/audit-2026-09-27.md` #13a |
| D-06 Storage | Raw Parquet flushed every 30 s or 1,600 rows; SQLite schema version stamped | `docs/OPERATING-GUIDE.md`, ADR-010 |

## Pending (level 4)

| ID | Missing evidence | Cheapest way to get it |
|---|---|---|
| P-01 | Loss and recovery across a controlled USB unplug, Arduino reset and killed host | Three logged 10-minute runs, one per action (`hardware-bringup`) |
| P-02 | Runtime stack headroom | Stack-paint check on the flashed `uno` build, or a documented bounded-usage argument |
| P-03 | Physical model metrics, false alarms per hour | Calibrate, then labelled physical runs (ADR-011); not before |
| P-04 | Real LED/buzzer response and alarm latency | Send SET_ALARM per state and record what lights and sounds; latency needs a logic analyzer or a shared clock |
| P-05 | Dashboard on a physical run | `sentinel --data data/physical_check api`, screenshot showing the PHYSICAL label |
| P-06 | Photos of the wiring and each module's part markings, wiring schematic, demo video | Phone photos before the next session; schematic from `docs/hardware/design.md` once confirmed; screen recording showing the SIMULATED/PHYSICAL label |
| P-07 | Tape-measure reference for the ultrasonic; probe dry/wet raw; thermistor part and beta; DHT11 vs DHT22 | ADR-011 procedure: 3 distances, probe in air then in water, part markings |
| P-08 | Rate jitter distribution | The raw Parquet already holds host arrival times (`host_timestamp_ns`): compute inter-arrival statistics offline from a copy of `data/physical_check` |

Report sample interval distributions separately from USB arrival jitter. Boot/time
wraps and known losses must not silently enter rate estimates. Future T0-T7 timing
requires a clock-domain method; see the architecture documentation.

## Re-audit 2026-09-29

Re-verified from files present in the repository: S-02 and S-03 numbers against the
JSON (all match; the validation file's isolation-forest and threshold accuracies are
0.167, not cited in S-03), D-01 constants against `firmware/include/config.h`, D-02
frame sizes against the `DATA` struct (29 B payload), D-04 window and state
thresholds against `windows.py` and `state.py`, D-06 flush rule against
`storage/database.py`, and the test count (S-01).

**Unverifiable in this checkout** (`data/` and `firmware/.pio` are git-ignored and
absent): every R-01..R-08 count and median, the 19,369 row total, the 1,398/1,367/31
invalid split, the 140 and 16 FAULT-episode counts (R-08), the S-04 summary tallies
and the S-05 compile sizes. They are retained as recorded on 2026-09-27. The
thermistor/DHT offsets are cross-checked only against `docs/hardware/bringup-log.md`,
which is a second document, not raw data.

Wording note: "invalid" means two different things. The ultrasonic distance-valid flag
was clear in 38.0% of the 1 h run's samples; the run summary's 38.9% also counts DHT
errors. "99.4-100% valid" for the other runs refers to the ultrasonic flag only (the
5 h run also had 1.5% DHT checksum errors).

## Historical: Phase 0 verification, 2026-09-15

Kept as a record; superseded by the tables above. Working tree foundation, no
hardware attached. The startup-message firmware built at flash 1,520 / 32,256 B and
static RAM 188 / 2,048 B (PlatformIO 6.1.19; atmelavr 5.1.0; framework-arduino-avr
5.2.0; GCC 7.3.0). Python 3.9.0 environment recorded in
`phase-0-python-environment.txt`. Four unused-parameter warnings come from Arduino
framework `new.cpp`. No acquisition result was claimed.

## Files in this directory

| File | What it is | Current? |
|---|---|---|
| `software-verification.md` | Dated verification narrative (2026-09-18 post-pivot, 2026-09-15 pre-pivot) | Current; test count in S-01 is newer |
| `host-profile-post-pivot.json` | S-02 | Current |
| `synthetic-model-validation.json`, `synthetic-model-test.json` | S-03 | Current, synthetic |
| `host-profile-pre-pivot.json`, `synthetic-model-*-pre-pivot.json`, `synthetic-stress-summary-pre-pivot.json` | Motor/vibration design | Historical only |
| `phase-0-python-environment.txt`, `software-python-environment.txt` | Package snapshots (the latter lists `fastapi==0.119.1` and `dash==3.4.0`, older than the venv in use on 2026-09-27: FastAPI 0.124.4, Starlette 0.49.3) | Historical snapshots |

# Software verification

> Two dated verification passes below: 2026-09-18 (post-pivot, tank/environmental
> design — see [ADR-008](../decisions/ADR-008-sensor-set-pivot.md)) and 2026-09-15
> (pre-pivot, motor/vibration design). Neither section's numbers apply to the
> other design; both are kept as an honest record of what was actually measured,
> when. **Everything here is synthetic/simulated or compile-time**; nothing on this
> page is physical-hardware acceptance.

## Software verification — 2026-09-18 (post sensor-set pivot)

### Scope

Everything in this section is SYNTHETIC: generated signals on the Windows host.
It contains no Uno measurement, no real fault classification and no measured
hardware alarm latency. (Real bring-up captures were made later, 2026-09-19/20 and
2026-09-23; they are uncalibrated, NORMAL-only and not part of this evidence -
see [failures](../failures/README.md).) Source was an uncommitted working tree on
this machine when these numbers were recorded, and code has changed since; the
figures below were not re-measured for this edit.

### Automated checks

- `python -m pytest -q`: **58 passed** (3.65 s observed 2026-09-18, not re-run
  since). The suite is 21 test functions plus one parametrized test with 37 split
  cases (58 total).
- Covers 37 binary split boundaries, CRC vector/recovery, sequence rollover,
  command retry/duplicate ACK behavior, the slow-signal feature math
  (constant/ramp/mismatch cases), persistence/recovery, invalid sensors/DHT
  checksum error, Parquet/SQLite, grouped ML, and API/WebSocket endpoints via
  FastAPI's `TestClient`, plus a mocked serial reconnect test and an injected
  status-file lock. The mock exercises the serial worker; it is not a USB test.
- There is no Dash test: the Dash dashboard was replaced by the React frontend on
  2026-09-19 and no test of a Dash callback exists in `tests/`. There is no
  automated frontend test either.

### Firmware compilation

PlatformIO 6.1.19, atmelavr 5.1.0, Arduino AVR framework 5.2.0, GCC 7.3.0,
SimpleDHT 1.0.15. The `uno` binary environment built successfully with no
SPI/I2C/OneWire in the design.

| Environment | Flash bytes / 32256 | Static SRAM bytes / 2048 |
|---|---:|---:|
| uno (binary, 1 Hz report), as recorded 2026-09-18 | 6856 | 375 |
| uno (binary), rebuilt 2026-09-27 (`platformio run -e uno`, not flashed) | 7212 | 394 |
| uno_csv (debug), rebuilt 2026-09-27 | 7576 | 392 |

These are compile-time sizes, not runtime stack measurements. The firmware changed
after the first row was recorded (the buzzer now uses `tone()`, 2026-09-19), which
the 2026-09-27 rebuild reflects. The 2026-09-27 firmware refactor (named constants,
`packed` `Sample`) left both builds' sizes unchanged (compared against the previous
source). Flash/SRAM were both below the pre-pivot build (7746/544)
because the SPI/I2C/OneWire drivers were replaced by plain digital/analog reads.

### Synthetic end-to-end observations

From the git-ignored run summaries in `data/smoketest` and `data/ml_smoketest`
(90 s of generated signal, 1 Hz, not curated JSON in this directory):

| Run | Duration | Records | Windows | State | Parser errors |
|---|---:|---:|---:|---|---:|
| CYCLE demo | 90 s | 90 | 5 | NORMAL | 0 |
| SENSOR_MISMATCH (3 runs) | 90 s | 90 | 5 | FAULT | 0 |
| Other five conditions (3 runs each) | 90 s | 90 | 5 | NORMAL | 0 |

Host timing, two sources. The curated microbenchmark
`host-profile-post-pivot.json` (100 iterations, model `threshold-demo-v1`,
tracemalloc on) gives feature extraction median **0.553 ms** (p95 0.773 ms) and
inference median **0.0014 ms** (p95 0.0025 ms), traced Python allocation peak
17,989 bytes. The 90 s CYCLE run summary in `data/smoketest` recorded medians of
0.4242 ms and 0.0016 ms. These are per-window host observations on this machine,
excluding serial travel and physical actuation. Generated timestamps produce exactly
1 Hz and zero jitter by construction; this validates analysis plumbing, not
sensor timing accuracy.

### Synthetic ML workflow

Generated 18 independent SYNTHETIC runs: 3 for each of the six conditions
(NORMAL, LOW_WATER, OVERFLOW, RAPID_DRAIN, SENSOR_MISMATCH,
ENVIRONMENTAL_ANOMALY), 90 s per run, 1,620 records and 90 feature windows in
total. Whole runs were split 6 train / 6 validation / 6 test (5 windows per class
in each of validation and test, 30 windows each).

Selection (validation, `synthetic-model-validation.json`): the **tree** was
selected under the documented ranking (fault recall, then false positives, then
simplicity), with validation fault_recall 1.0, false_positive_rate 0.0 and
accuracy 0.867. The random forest tied on fault recall/false positives (accuracy
0.90) but is less simple; logistic regression scored fault_recall 0.96 with
false_positive_rate 0.6; Isolation Forest 0.72 / 0.0; the level-disagreement
threshold baseline 0.20 / 0.0 (the 0.2 fault recall quoted in an earlier version of
this note belongs to that baseline, not to the selected model).

Held-out test (`synthetic-model-test.json`, 30 windows, run once after selection,
model sha256 `de44dac6...59284eb9`): accuracy 0.80, fault_recall 0.96,
false_positive_rate 0.20, 1 missed fault window, ROC AUC 0.88, PR AUC 0.955. Errors
are LOW_WATER confused with RAPID_DRAIN (2 and 2) and NORMAL with OVERFLOW (1 each
way); ENVIRONMENTAL_ANOMALY and SENSOR_MISMATCH were classified perfectly. This
demonstrates the split/train/evaluate path on a very small synthetic dataset -
**not a physical diagnostic performance claim**, and not a result to read much into
given 30 windows per split. The pre-pivot `*-pre-pivot.json` files are the
2026-09-15 evidence (motor-monitoring labels IMBALANCE_*/LOOSE_MOUNT) kept for the
historical record.

### Reproduce and extend

Use fresh output directories and the commands in the operating guide. Pending:
hardware rates/jitter, USB throughput beyond the uncalibrated bring-up captures,
runtime stack headroom, physical fault metrics, synchronized end-to-end latency,
and any tank demonstration footage.

---

## Software verification — 2026-09-15 (pre-pivot, motor/vibration design)

## Scope

All runs below use synthetic signals on the Windows host. No Uno upload, physical
sampling test, real fault classification or measured hardware alarm latency was
performed. Compilation resource figures are real build outputs; they are not
runtime SRAM/stack measurements. Source is an uncommitted working tree.

## Automated checks

- `python -m pytest -q`: **53 passed** (6.10 s observed, final suite).
- Covers 35 binary split boundaries, CRC vector/recovery, sequence rollover,
  command retry/duplicate ACK behavior, analytic DSP, persistence/recovery,
  invalid sensors/overflow, Parquet/SQLite, grouped ML, API/WebSocket and (at that
  date) a Dash callback request producing chart JSON. That Dash test was removed
  with the Dash dashboard on 2026-09-19; no such test exists now.
- Includes a mocked serial cable-loss/reconnection test and a Windows status-file
  locking regression. The mock exercises the serial worker; it is not a USB test.
- `python -m pip check`: no broken requirements in the project venv.
- Store audit on the generated research dataset: no missing/orphaned/partial files
  or unfinished runs.

## Firmware compilation

PlatformIO 6.1.19, atmelavr 5.1.0, Arduino AVR framework 5.2.0, GCC 7.3.0,
OneWire 2.3.8. All environments build successfully.

| Environment | Flash bytes / 32256 | Static SRAM bytes / 2048 |
|---|---:|---:|
| uno (binary, 800 Hz target) | 7746 | 544 |
| uno_csv (100 Hz debug) | 8218 | 544 |
| uno_edge (optional threshold) | 7804 | 545 |

The optional threshold adds 58 flash bytes and one static byte in these builds.
It is not equivalent to the host classifier. No inference-time/power comparison
has been measured. Initial compiler warnings were unused parameters inside the
Arduino framework's `new.cpp`; project modules compiled successfully.

## Synthetic end-to-end observations

| Run | Generated duration | Records | Windows | Detected sequence/CRC errors |
|---|---:|---:|---:|---:|
| Threshold CYCLE | 24 s | 19200 | 47 | 0 / 0 |
| Trained-model CYCLE | 24 s | 19200 | 47 | 0 / 0 |
| Threshold benchmark | 60 s | 48000 | 119 | 0 / 0 |
| NORMAL stress rerun | 300 s | 240000 | 599 | 0 / 0 |

The 60 s signal benchmark completed in about 4.437 s wall time (4.375 s process
CPU). This is accelerated generated-data processing, not a real-time hardware
soak. Observed median three-axis feature time was 1.008 ms and threshold score
time 0.0052 ms. On the trained-model CYCLE run, medians were 0.9712 ms features
and 0.4392 ms inference. These are per-window host observations on this machine;
they exclude serial travel, initial window fill and physical output actuation.

Generated timestamps produce exactly 800 Hz and zero jitter by construction.
Those values validate analysis plumbing, not the sensor's timing accuracy.

The initial 300 s generated-signal stress attempt failed during Windows replacement
of `status.json` (WinError 5). Raw records were finalized and the run marked FAILED.
After making live status best-effort, the rerun completed in 34.375 s wall time,
33.4375 s process CPU, with one skipped status publication and zero acquisition
gaps/parser errors. This preserves the failure history rather than omitting it.
Median feature time during this concurrent-load run was 1.8318 ms; results depend
on host load and are not a hard deadline guarantee. The run summary is kept as
`synthetic-stress-summary-pre-pivot.json` (800 Hz era, pre-pivot only).

`host-profile-pre-pivot.json` records a separate generated-input microbenchmark with traced
Python allocations. It measures FFT/features/inference and allocation peak, not
total RSS or any physical latency. Curated run/model JSON evidence is kept in
this directory; full data and artifacts remain in ignored `data/`.

## Synthetic ML workflow

Generated 20 independent runs (5 per each of four conditions), 8 s/run,
128000 raw samples and 300 overlapping feature windows. Run groups were split
into 12 train, 4 validation and 4 test runs. Logistic regression was selected
under the documented validation ranking. Held-out synthetic classification was
perfect on this deliberately separable generator; **this is not a physical
diagnostic performance claim**. It demonstrates the split/train/evaluate path.

Full local artifacts: `data/models/synthetic-v1/report.json`, `splits.json`,
`test-report.json`, `model.joblib`; raw datasets in `data/research`. A separately
generated CYCLE run exercises the selected model without changing frozen research
data. Synthetic models are rejected by physical inference.

## Reproduce and extend

Use fresh output directories and the commands in the operating guide. Raw summary
JSON files are associated with run IDs in each data directory. The standalone
waveform/FFT report from that date is the git-ignored
`data/reports/sentinel-demo.html` (pre-pivot; the current `report` command draws
tank-level and DHT charts instead).

Pending: hardware rates/jitter, USB throughput, sensor loss, runtime stack
headroom, total process RSS, physical fault metrics, synchronized end-to-end
latency and guarded-rig demonstration footage.

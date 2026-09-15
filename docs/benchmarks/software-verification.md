# Software verification — 2026-09-15

## Scope

All runs below use synthetic signals on the Windows host. No Uno upload, physical
sampling test, real fault classification or measured hardware alarm latency was
performed. Compilation resource figures are real build outputs; they are not
runtime SRAM/stack measurements. Source is an uncommitted working tree.

## Automated checks

- `python -m pytest -q`: **53 passed** (6.10 s observed, final suite).
- Covers 35 binary split boundaries, CRC vector/recovery, sequence rollover,
  command retry/duplicate ACK behavior, analytic DSP, persistence/recovery,
  invalid sensors/overflow, Parquet/SQLite, grouped ML, API/WebSocket and an actual
  Dash callback request producing chart JSON.
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
on host load and are not a hard deadline guarantee.

`host-profile.json` records a separate generated-input microbenchmark with traced
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
waveform/FFT report is `data/reports/sentinel-demo.html`.

Pending: hardware rates/jitter, USB throughput, sensor loss, runtime stack
headroom, total process RSS, physical fault metrics, synchronized end-to-end
latency and guarded-rig demonstration footage.

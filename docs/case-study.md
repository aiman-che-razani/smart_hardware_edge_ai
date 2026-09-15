# SentinelDAQ engineering case study — implementation draft

## Problem

An existing Arduino Uno must acquire vibration alongside slower electrical and
thermal measurements, stream those readings to a Windows PC and respond to
acknowledged health-state commands. The project investigates acquisition quality
and operational behavior rather than treating a model accuracy score as the system.

## Implemented system

ADXL345 SPI FIFO, INA219 I2C and DS18B20 1-Wire drivers are separate C++ modules.
The 800 Hz binary build shares one cooperative loop with bounded command parsing
and alarm service. The PC owns vibration windows, FFT, features and inference.
Parquet preserves raw runs; SQLite indexes experiments and stores derived results.
A read-only API and Dash dashboard expose current and historical state.

The repository includes a byte-level simulator using the same frame codec as the
host parser, independent synthetic runs, grouped train/validation/test manifests,
model comparisons, fault injection and standalone waveform/spectrum exports.

## Engineering trade-offs

- 34-byte data frames require 272000 bits/s at 800 Hz. 500000 baud is a proposed
  capacity fit; hardware throughput has not been measured.
- An 800-sample int16 XYZ window needs 4800 bytes, exceeding Uno's 2 KB SRAM.
  Host-side processing keeps the embedded memory footprint small.
- Firmware uses FIFO readout timestamps. They are honest service-time observations,
  not fabricated sensor conversion timestamps. Timing quality remains a hardware
  experiment, especially while servicing 1-Wire transactions.
- Latest current/temperature readings have validity and ages. They are not
  represented as simultaneously sampled vibration data.
- UNKNOWN is explicit after gaps and loss of contact. Persistent FAULT requires
  multiple windows; a hardware alarm remains latched if the host disappears.
- Grouped run splits reduce leakage from overlapping windows. Synthetic models
  are explicitly blocked from physical inference.

## Evidence

See [verification results](benchmarks/software-verification.md) for actual test,
compile and software timing observations. Synthetic model scores demonstrate the
training/evaluation code path only. They cannot support claims of diagnostic
accuracy, robustness to real motors, safe fault detection or generalization.

## Remaining portfolio evidence

Hardware identity and photos, final breakout-specific schematic, guarded rig
photos, physical dataset, measured jitter/throughput/stack headroom, physical
confusion matrices, operational false alarms/hour and a demonstration video are
pending. Do not fill these gaps with stock photos or simulated numbers presented
as measurements. The next engineering step is the documented static orientation
test, followed by multi-sensor timing validation.

## Demo recording outline

1. Show the SIMULATED source label and architecture.
2. Run a 60-second real-time CYCLE simulation; point out warning/fault/recovery.
3. Show raw waveform/FFT, historical run comparison and DAQ counters.
4. Inject corrupt frames and show gaps/reset windows without invented continuity.
5. Open model split manifest and synthetic evaluation report; explain why these
   are integration tests rather than a real machine-performance result.
6. Show Uno build resource sizes and list the physical measurements still needed.

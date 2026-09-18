# Phase 1 plan and acceptance criteria

> **Historical/superseded.** Written for the original ADXL345 vertical slice
> before the sensor-set pivot to tank/environmental monitoring — see
> [ADR-008](decisions/ADR-008-sensor-set-pivot.md). The current Phase 1 (HC-SR04
> ultrasonic slice) is described in [PHASE-STATUS.md](PHASE-STATUS.md) and the
> bring-up steps in [OPERATING-GUIDE.md](OPERATING-GUIDE.md#hardware-bring-up-pending).
> Kept as-is for the historical record; the ADXL345-specific detail below no
> longer applies.

## Objective

Demonstrate ADXL345 → Uno → USB → Python live XYZ at a conservative initial rate.
No motor, current/temperature sensor or ML is needed for this vertical slice.

## Prerequisites

Complete Phase 0 build/import checks. Identify exact Uno and ADXL345 modules;
verify voltage/interface design in `hardware/design.md` before wiring. Record COM
port and module photos/schematic. A final wiring diagram depends on those modules.

## Planned implementation

Add modular accelerometer driver and minimal CSV sender to firmware, shared raw
types/config, and Python serial reader/parser with explicit engineering-unit
conversion. Add PySerial only then, for Windows serial access. Begin with 100 Hz
ODR, full-resolution ±2 g configuration; read back configuration. Agree exact SPI
mode/clock and CSV grammar against the datasheet before implementing them.

## Verification procedure and expected behavior

1. With motor disconnected, check power/logic rails and connect verified SPI nets.
2. Build/upload, open the identified COM port at the agreed baud. Expect boot and
   configuration records, device ID 0xE5, and changing XYZ records. Wrong ID must
   produce a clear error, not plausible synthetic measurements.
3. Read back ODR/range/full-resolution configuration and record raw/unit scaling.
4. Place sensor in six static orientations, approximately +X/-X/+Y/-Y/+Z/-Z up.
   Record 5 s mean per orientation. Gravity should move to the corresponding axis
   with reversed sign; the vector magnitude should be roughly 1 g.
5. Provisional bring-up tolerance: magnitude 0.8–1.2 g after settling. Investigate
   offsets, alignment, scale or hardware if outside; this is not calibration proof.
6. Observe live data for 60 s; record valid/malformed lines, sequence gaps, effective
   delivered rate, reset count, board/config and Python/firmware versions. Target
   >=90 valid records/s at the proposed 100 Hz setting with zero unexplained gaps
   or malformed lines on a clean link. Precise timing validation belongs to Phase 2.
7. Inject malformed/truncated input into host parser; it must recover at a valid
   line boundary and increment diagnostics. Stop host with Ctrl+C; port must close.
8. Test missing sensor at startup with power removed before changing wiring;
   firmware must report detection failure. Full reconnect handling comes in Phase 5.

Acceptance: correct identity/readback, orientation checks, usable live display,
recorded clean-link evidence, parser recovery and clean shutdown demonstrated.
Potential failures include crossed MOSI/MISO, wrong CS, voltage mismatch, incorrect
SPI mode, port busy, charge-only cable, auto-reset and line endings. Diagnose before
rewriting code. Stop and review evidence before Phase 2.

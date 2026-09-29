# SentinelDAQ

Arduino-based tank & environmental monitoring: sensors → Uno → USB → Python,
with a host-controlled LED/buzzer alarm (implemented in firmware; the host
command/ACK path is tested against a simulator; the real LED/buzzer response is
not yet verified).

## Status

**Software implementation with simulation-based verification, plus first
uncalibrated hardware bring-up captures.** Modular Uno firmware, binary/CSV
transport, Python acquisition, DSP, grouped ML, local storage, a JSON API and a
React web UI are implemented. The LED/buzzer alarm is implemented in firmware and
its host command/ACK path is tested against a Python simulator; the physical
LED/buzzer response and latency are unmeasured.

The Uno binary firmware has been uploaded and real captures exist: 6 runs on
2026-09-19/20 (`data/physical`, 19,369 raw rows across the runs that hold data,
including one ~5 h run) and a 20 s plus a 1 h run on 2026-09-23
(`data/physical_check`, the 1 h run has 3,598 samples with no sequence gaps or
parser errors, but 38.0% of *that run's* samples had no valid ultrasonic echo
(38.9% invalid once 31 DHT errors are counted); the other captures had
99.4-100% valid ultrasonic echoes, so the dropout is one session's problem, not
a constant rate, and its cause is not established; see the
[evidence ledger](docs/benchmarks/README.md)). These are **bring-up captures, not a dataset and not
acceptance evidence**: every run is labelled NORMAL, nothing is calibrated (no
tape-measure distances, no measured water-probe dry/wet range, placeholder
thermistor constants), the water probe sat at its dry floor for the long run, and
the ultrasonic sensor was at times not aimed at a tank. There is no physical
model and no physical calibration. Synthetic results are labelled and cannot be
deployed as physical models. Details: [failures](docs/failures/README.md),
[audit ledger](docs/audit-2026-09-27.md).

## Run the demo

From this repository in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/demo simulate --seconds 60 --realtime
```

In a second terminal:

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/demo api
```

Open **http://127.0.0.1:8000** (once `frontend/` has been built — see the
[operating guide](docs/OPERATING-GUIDE.md) — otherwise this serves `/api/*`
JSON only). For installation, model research, hardware bring-up and
verification commands, see the [operating guide](docs/OPERATING-GUIDE.md).

## Start here

1. [Operating guide](docs/OPERATING-GUIDE.md) — run, tune, test and collect evidence.
2. [Phase coverage](docs/PHASE-STATUS.md) — implemented paths and pending acceptance.
3. [BOM, pin allocation and power](docs/hardware/design.md) — review before wiring.
4. [Implemented serial protocol](docs/protocol/v1.md) — framing, units and commands.
5. [Case study](docs/case-study.md) — design trade-offs and evidence limitations.

## Repository

```text
firmware/                 PlatformIO binary and CSV debug builds
  include/                configuration, fixed-width types and protocol
  src/                    sensors, acquisition, communication, actuators
python/sentinel/          DAQ, DSP, ML, storage, API, CLI
frontend/                 React web UI (Vite) — consumes the JSON API
docs/
  requirements.md         V1 specification, assumptions, acceptance mapping
  architecture/           system, scheduling and module boundaries
  hardware/               BOM, proposed pinout and power design
  protocol/               implemented serial protocol v1 and transport notes
  decisions/              architecture decision records
  experiments/            run metadata template and data-governance policy
  benchmarks/             measured evidence ledger
  failures/               risk register and observed failures
  audit-2026-09-27.md     findings-and-status ledger from the 2026-09-27 audits
tests/                    protocol, DSP, storage, ML and integration tests
```

## Roadmap and phase gate

0 foundation → 1 ultrasonic slice → 2 deterministic sampling → 3 transport →
4 complete sensing → 5 robust DAQ/storage → 6 signal processing → 7 dataset →
8 grouped ML research → 9 live inference → 10 alarm control → 11 API/dashboard →
12 verification → 13 portfolio → 14 deferred (stepper/IR reserved pins only).

Software across phases was authorized, with simulation selected until hardware
details are available. Physical acceptance remains phase-by-phase; see
[phase coverage](docs/PHASE-STATUS.md). The sensor set was pivoted from motor/
vibration monitoring to tank/environmental monitoring — see
[ADR-008](docs/decisions/ADR-008-sensor-set-pivot.md). The original brief in
[docs/project-brief.md](docs/project-brief.md) is a historical record of how
the project started and no longer describes the current system.

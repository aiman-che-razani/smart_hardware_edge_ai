# SentinelDAQ

Arduino-based machine condition monitoring: sensors → Uno → USB → Python,
with a future host-controlled LED/buzzer alarm.

## Status

**Software implementation with simulation-based verification.** Modular Uno
firmware, binary/CSV transport, Python acquisition, DSP, grouped ML, local storage,
API and dashboard are implemented. Hardware validation and a physical dataset are
pending. Synthetic results are labelled and cannot be deployed as physical models.

## Run the demo

From this repository in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/demo simulate --seconds 60 --realtime
```

In a second terminal:

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/demo dashboard
```

Open **http://127.0.0.1:8050**. For installation, model research, hardware bring-up
and verification commands, see the [operating guide](docs/OPERATING-GUIDE.md).

## Start here

1. [Operating guide](docs/OPERATING-GUIDE.md) — run, tune, test and collect evidence.
2. [Phase coverage](docs/PHASE-STATUS.md) — implemented paths and pending acceptance.
3. [BOM, pin allocation and power](docs/hardware/design.md) — review before wiring.
4. [Implemented serial protocol](docs/protocol/v1.md) — framing, units and commands.
5. [Case study](docs/case-study.md) — design trade-offs and evidence limitations.

## Repository

```text
firmware/                 PlatformIO binary, CSV and optional edge builds
  include/                configuration, fixed-width types and protocol
  src/                    sensors, acquisition, communication, actuators
python/sentinel/          DAQ, DSP, ML, storage, API, dashboard, CLI
docs/
  requirements.md         V1 specification, assumptions, acceptance mapping
  architecture/           system, scheduling and module boundaries
  hardware/               BOM, proposed pinout and power design
  protocol/               transport plan (not a frozen wire specification)
  decisions/              architecture decision records
  experiments/            future run metadata and data governance
  benchmarks/             measured evidence ledger
  failures/               risk register and observed failures
tests/                    protocol, DSP, storage, ML and integration tests
```

## Roadmap and phase gate

0 foundation → 1 vibration slice → 2 deterministic sampling → 3 transport →
4 complete sensing → 5 robust DAQ/storage → 6 signal processing → 7 dataset →
8 grouped ML research → 9 live inference → 10 alarm control → 11 API/dashboard →
12 verification → 13 portfolio → 14 optional edge classifier.

Software across phases was authorized, with simulation selected until hardware
details are available. Physical acceptance remains phase-by-phase; see
[phase coverage](docs/PHASE-STATUS.md). See the original brief in
[docs/project-brief.md](docs/project-brief.md).

# Evidence ledger

> Phase 0 history below. Current results are in
> [software verification](software-verification.md); hardware measurements remain pending.

No sensor, serial-throughput, ML or end-to-end benchmarks have been measured.
Configured rates and architecture calculations are not benchmark results.

For every measurement record date, commit/config, hardware, method, duration,
raw evidence path, summary and limitations. Store large logs outside Git.

| Quantity | Status |
|---|---|
| Actual sample rates, jitter, loss | Not measured |
| Throughput / CRC failures | Not measured |
| Phase 0 smoke firmware flash/static SRAM | 1520 / 188 bytes; see verification below |
| Runtime stack headroom | Not measured |
| Host processing / feature / ML latency and resources | Not implemented |
| Model metrics / false alarms per hour | No dataset or model |
| Physical alarm activation latency | Not measured |

Report sample interval distributions separately from USB arrival jitter. Boot/time
wraps and known losses must not silently enter rate estimates. Future T0–T7 timing
requires a clock-domain method; see architecture documentation.

## Phase 0 verification — 2026-09-15

Working tree foundation, not yet committed; no hardware attached or upload tested.

- `python -m sentinel` in project venv: passed, expected Phase 0 message.
- `python -m pip check`: passed, no broken requirements.
- Python syntax, Uno board/baud configuration and local Markdown links: passed.
- `platformio run --project-dir firmware`: SUCCESS, release Uno build.
- PlatformIO 6.1.19; atmelavr 5.1.0; framework-arduino-avr 5.2.0;
  toolchain-atmelavr 1.70300.191015 (GCC 7.3.0).
- Build reported flash 1520 / 32256 bytes and static RAM 188 / 2048 bytes.
  This is the startup-message program only, not the future sensing firmware.
  Stack usage and runtime headroom were not measured.
- Four unused-parameter warnings originate in Arduino framework `new.cpp` under
  `-Wextra`; no project-source warnings appeared. Build succeeded.
- Local Git branch `main` initialized; origin fetch/push URL matches the supplied
  GitHub repository. Remote query returned no refs. No commit or push performed.
- Python 3.9.0 venv created; pip updated from 20.2.3 to 26.0.1 to support editable
  pyproject installation. Resolved packages: `phase-0-python-environment.txt`.

Phase 0 software checks pass. Hardware identification, wiring review and physical
verification remain prerequisites to Phase 1. No acquisition results are claimed.

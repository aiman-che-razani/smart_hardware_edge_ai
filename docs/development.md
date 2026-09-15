# Development setup and Phase 0 verification

> Historical Phase 0 setup. Use [the current operating guide](OPERATING-GUIDE.md)
> for the implemented system; firmware no longer prints the Phase 0 message.

## Environment and dependencies

Use Windows PowerShell, Git, Python with pip/venv, and PlatformIO Core (or VS Code
PlatformIO). Python 3.9 can run this foundation; prefer Python 3.11/3.12 for later
scientific dependencies. The locally available `python` is 3.9.0; `py` currently
does not discover an interpreter, so commands use `python`.

- setuptools builds the small installable host package.
- PlatformIO 6.1.19 manages the Uno compiler/framework/build; AVR platform 5.1.0
  is pinned in `firmware/platformio.ini` for an explicit initial toolchain.
- pytest is reserved for behavior tests introduced with acquisition.
- There are no host runtime dependencies in Phase 0. Add PySerial in Phase 1,
  numerical/storage/ML packages only in their relevant phases.

PlatformIO itself installs transitive dependencies including PySerial and web
server libraries. These are development-tool internals; SentinelDAQ does not
start a server or depend on them at runtime in Phase 0. The observed environment
is recorded in `benchmarks/phase-0-python-environment.txt` (an inventory, not a
portable lockfile).

## Run from repository root

```powershell
Set-Location 'C:\Users\nadee\Documents\smart_hardware_edge_ai'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m sentinel
$env:PLATFORMIO_CORE_DIR = Join-Path (Get-Location) '.pio'
.\.venv\Scripts\python.exe -m platformio run --project-dir firmware
git remote -v
git status --short --branch
```

First installation/build needs internet access. Setting PLATFORMIO_CORE_DIR keeps
downloaded tools/cache inside this workspace. Activation is optional; explicit
interpreter paths avoid PowerShell activation-policy issues. If Git reports owner
mismatch in the sandbox, add `-c safe.directory=C:/Users/nadee/Documents/smart_hardware_edge_ai`
to that Git invocation. Do not use a wildcard global exception.

## Expected results and acceptance

The package prints `SentinelDAQ 0.0.1: Phase 0 environment ready; acquisition not implemented.`
PlatformIO reports a successful Uno build and flash/static RAM sizes. This proves
the toolchain can build a minimal program, not that sensors work. Record command
results/tool versions and limitations in `benchmarks/README.md`. No behavioral
pytest tests exist yet; do not report an empty suite as a pass.

Optional hardware smoke check: disconnect all external wiring, connect Uno via
USB, identify its port with `python -m platformio device list`, and use the venv
interpreter for `-m platformio run --project-dir firmware --target upload --upload-port COMx`.
Then run `-m platformio device monitor --port COMx --baud 115200`; press reset if
the startup line was missed. Expected: `SentinelDAQ phase 0: no acquisition` once
per reset. Upload replaces existing firmware; preserve any valuable sketch first.
Hardware upload is not performed automatically during Phase 0.

Likely environment failures: registry access blocked, unavailable compiler download,
wrong Python path or COM driver. Keep exact error output, fix the cause and rerun
the affected check. Phase 0 ends after specification review and successful host
and compile checks. Phase 1 wiring remains gated on exact breakout identification.

## Tool references

- [PlatformIO Uno configuration](https://docs.platformio.org/en/latest/boards/atmelavr/uno.html)
- [PlatformIO package](https://pypi.org/project/platformio/)

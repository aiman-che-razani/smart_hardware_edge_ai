# Test policy

Run `.venv/Scripts/python.exe -m pytest -q` from the repository root.
Tests cover parser recovery, CRC vectors, rollover, commands, DSP, window gaps,
alarm transitions, storage, grouped ML, API/UI integration and simulated failures.
See `docs/failures/verification-matrix.md` for hardware tests still pending.

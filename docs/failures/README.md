# Initial risk register

Owner: project engineer. All mitigation checks remain open until evidence exists.

| Risk | Impact / priority | Mitigation and verification |
|---|---|---|
| Unknown ADXL345 voltage interface | Sensor damage / high | Obtain schematic, check rails and logic translation before wiring |
| Motor stall or transient exceeds shunt/supply rating | Heat/damage / high | Confirm stall current, fuse, shunt power and suppression |
| Rotating part escapes / exposed fixture | Injury / high | Guard and inspect fixture; no improvised running fault modifications |
| CSV exceeds serial capacity | Silent sample loss / high | Begin at 100 Hz; byte budget and binary measurement later |
| Blocking temperature/I2C/serial activity | Vibration gaps / high | Async conversion, bus timeouts, bounded writes, FIFO/loss counters |
| SRAM/stack exhaustion | Reset/corruption / high | Static buffers, build-size ledger, runtime headroom testing |
| Ground noise / long SPI wiring | Corruption / medium | Short wiring, separate motor returns, decoupling and analyzer checks |
| Aliasing or weak sensor mounting | Misleading spectrum / high | Review bandwidth, rigid mounting and repeatability before interpretation |
| USB reset/disconnect or timestamp wrap | False continuity / high | Sessions, boot records, rollover/reconnect tests |
| Stale current/temp shown as fresh | Misleading features / medium | Validity, age and independent update times |
| Overlapping-run ML leakage | Inflated results / high | Split by run; fit transforms on train only |
| Lost commands / false alarms | Unreliable indication / high | ACK/retry, idempotency, hysteresis and explicit communication state |
| Python 3.9 scientific dependency support | Installation friction / medium | Move to maintained Python before later dependencies |

## Observed development issues

- Sandbox user differs from repository owner: use a command-local Git
  `safe.directory` exception for this exact project, not a global wildcard.
- Sandbox restricts `.git` writes and network access; repository connection needs
  the corresponding tool approval.
- PlatformIO was not installed in the system Python at initial inspection.
- A generated-data stress run encountered Windows `WinError 5` while atomically
  replacing `status.json`. The run was marked FAILED and stored data was finalized.
  Live status is now published at most five times per second, and a transient
  PermissionError skips that snapshot instead of stopping DAQ. The next update
  retries; stale snapshots display UNKNOWN. A regression test injects this lock.

For new failures record date, phase, reproduction, expected/observed behavior,
raw evidence, root cause, fix and regression check. Do not mark risks resolved
merely because a mitigation has been proposed.

# Initial risk register

Owner: project engineer. All mitigation checks remain open until evidence exists.

| Risk | Impact / priority | Mitigation and verification |
|---|---|---|
| Water contacting the Uno, breadboard or USB connection | Sensor/board damage / high | Route the water-level probe's leads away from logic wiring; keep the tank and electronics physically separated |
| Unknown module supply voltage (water-level, DHT) | Sensor/board damage / medium | Confirm each module's rated voltage against its datasheet before wiring to Uno 5V |
| Blocking DHT read stalls the main loop | Missed ultrasonic pings / medium | DHT read is bounded (~ms via SimpleDHT) and polled at most every 2s; confirm actual blocking duration on real hardware |
| SRAM/stack exhaustion | Reset/corruption / high | Static buffers, build-size ledger, runtime headroom testing |
| Uncalibrated water-level/thermistor readings | Misleading level/temperature values / high | Measure the actual dry/wet ADC range and thermistor part before trusting `pipeline.py`'s placeholder constants |
| USB reset/disconnect or timestamp wrap | False continuity / high | Sessions, boot records, rollover/reconnect tests |
| Stale DHT reading shown as fresh | Misleading features / medium | Validity, age (4s threshold) and independent update times |
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

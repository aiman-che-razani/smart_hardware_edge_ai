# ADR-009 — Serial wire protocol v1: length-delimited binary frames with CRC-16 and single-command ACK

Status: accepted; implemented in `firmware/src/communication/serial_protocol.cpp`
and `python/sentinel/acquisition/`. Verified against the Python simulator and, for
DATA/STATUS streaming only, in the 2026-09 bring-up captures (no parser errors in a
~5 h and a 1 h capture). The command/ACK and reconnect paths are not yet tested on
real hardware. Field tables are in [protocol/v1.md](../protocol/v1.md).

## Decision

Replace the readable CSV V0 debug format (ADR-006) for full acquisition with binary
protocol v1 over 115200 baud 8N1:

- **Framing:** `A5 5A`, version (1), type, payload length (0-40), payload, CRC-16.
  No end marker and no escaping; length plus CRC delimit a frame. On a bad header,
  version, length or CRC the parser discards one byte and rescans; an incomplete
  frame expires after a 500 ms inter-byte timeout, so resynchronisation is bounded.
- **Integrity:** CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection,
  xorout 0) over version, type, length and payload; the check value for ASCII
  `123456789` is 0x29B1. It catches accidental corruption only; it is not
  authentication.
- **Sizes:** payload plus 7 bytes of framing. DATA 29 -> 36 bytes on the wire,
  STATUS 10 -> 17, ACK 4 -> 11, host commands 3 -> 10. One DATA and one STATUS per
  second is about 53 bytes/s, under 0.5% of the link's ~11,520 bytes/s.
- **Commands:** SET_ALARM, CLEAR_ALARM, START_STREAM, STOP_STREAM, PING and
  GET_CONFIG each carry a 16-bit command ID and one value byte. The host keeps
  **one command in flight**, waits 500 ms for an ACK, and retries the identical bytes
  up to three attempts in total; the ACK must match both ID and command type.
  Commands are naturally idempotent (setting the same alarm state twice changes
  nothing), so a lost ACK is repaired by a retry, and firmware keeps no command
  history. Firmware replies are best effort in a bounded UART buffer.
- **Identity and continuity:** every DATA record carries a boot ID (EEPROM counter),
  a 32-bit sequence incremented per assembled report even if TX drops it, and a
  32-bit `millis()` timestamp; the host treats a boot change or reconnect as a new
  session and counts gaps, duplicates and resets.

## Consequences

- Bandwidth is not a design constraint at 1 Hz; the reasons for binary are integrity
  (CRC and bounded resync) and unambiguous field widths, not throughput.
- The struct layout is the wire layout: the layout is asserted for AVR builds.
  `Sample` is declared `packed` since 2026-09-27 (the build size is unchanged; it has
  not been flashed or tested on hardware), and the wire limits are named constants in
  `firmware/include/config.h` (`kProtocolVersion`, `kMaxPayload`) that must match
  `protocol.py`. A host-native build of the firmware types is still not a supported
  target.
- Reserved flag bits are simply unused; only bits 0-2 are set. Any addition needs a
  version bump or an explicit compatibility rule.
- One command in flight serialises all control traffic: a stuck transaction delays
  the next command until it fails after three attempts (about 1.5 s).
- Alarm semantics live partly in the protocol: any valid SET_ALARM/CLEAR_ALARM
  overrides the device state, including FAULT, so FAULT is not a hard latch (see
  [architecture](../architecture/system.md)).
- Firmware does not report its own version, so the host's firmware version string
  is declared, not measured.
- Unplug/replug, Arduino reset and USB throughput behaviour remain unmeasured (see
  the [verification matrix](../failures/verification-matrix.md)).

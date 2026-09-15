# Progressive transport plan

> This is the original plan. See [V1 specification](v1.md) for the implemented
> binary format and final V0 CSV field order.

Phase 1 introduces a minimal, formally documented CSV subset for live XYZ.
Phase 3 extends and hardens V0 before implementing binary V1. This reconciles
early readable acquisition with the later dedicated transport phase.

Proposed early record: `D,sequence,timestamp_us,ax_raw,ay_raw,az_raw`.
Specify integer ranges, line termination, maximum length, boot/config records,
units and malformed-line behavior when implementing it. No parser exists yet.

V1 design must freeze byte order, framing/escaping, maximum payload, CRC16
polynomial/init/reflection/xorout and test vectors before code is written. Include
DATA, STATUS, ACK, ERROR and SET_ALARM, CLEAR_ALARM, START_STREAM, STOP_STREAM,
PING, GET_CONFIG. Define unknown-version/type handling, parser resynchronization,
incomplete-frame timeout, boot/session identity and sequence/timer rollover rules.
Do not rely on a marker alone if it can occur inside payload bytes.

Data must carry sequence/time, raw XYZ, latest current/temperature and status, with
unambiguous validity/freshness. Consider batching to fit bandwidth; bound latency.
Command IDs and idempotent state-setting allow retries. Define ID lifetime across
reset, retry limits and ACK timeout. On link loss, display communication-unknown
rather than claiming NORMAL; final latched-alarm/timeout behavior requires Phase 10
tests. CRC detects accidental corruption; it is not authentication.

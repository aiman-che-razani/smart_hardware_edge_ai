# SentinelDAQ firmware (Arduino Uno, ATmega328P)

Owner: the `firmware` role. Verified against the source in the working tree on
2026-09-27 (uncommitted same-day fix pass: named constants in `config.h`, `packed`
`Sample`). Every `path:line` below is relative to `firmware/`. Anything not
verified in this pass is marked **unmeasured** or **not verified**.

**Build only.** Nothing in this document, and no firmware review, uploads to or talks
to the board. A firmware change is not done until the user uploads it and repeats
the hardware checks in `docs/failures/verification-matrix.md`. As of this
revision the binary build has been uploaded once and captured (see
`docs/PHASE-STATUS.md`); the 2026-09-27 refactor build has **not** been flashed.

## 1. Platform

Uno R3, ATmega328P at 16 MHz, 2048 B SRAM, 32256 B usable flash, no FPU. PlatformIO
`atmelavr@5.1.0`, `framework-arduino-avr` 5.2.0, avr-gcc 7.3.0, `SimpleDHT` 1.0.15
(`platformio.ini:1-14`). Flags `-Wall -Wextra`. No heap in project code (no `new`,
`malloc`, `String` anywhere under `src/` or `include/`), no recursion, no ISRs of our
own, no watchdog, no interrupt masking in project code (SimpleDHT 1.0.15 does not
mask interrupts either; grep of `SimpleDHT.cpp` for `cli`/`noInterrupts`: none).
Cooperative polling: `loop()` = `transport::poll()`, `sampler::poll()`,
`alarm::poll()` (`src/main.cpp:20-24`).

## 2. Module map

| Module | Files | Responsibility |
|---|---|---|
| main | `src/main.cpp` | Boot counter (EEPROM 0-3), init order, `loop()` |
| config | `include/config.h` | All timing constants, wire limits, pin map (namespace `sentinel`) |
| types | `include/types.h` | `Sample` (29-byte packed wire struct, `static_assert` at `:12`) |
| protocol enums | `include/protocol.h` | `Message` kinds (DATA=1 .. GET_CONFIG=21), `crc16` declaration |
| sampler | `src/acquisition/sampler.cpp` | Schedules sensors, assembles `Sample` once per report, STATUS cadence |
| serial protocol | `src/communication/serial_protocol.cpp` | Framing, CRC, RX parser, command dispatch, ACK/ERROR, TX with drop-on-full |
| alarm | `src/actuators/alarm.cpp` | LED/buzzer state machine, host-silence fallback |
| ultrasonic | `src/sensors/ultrasonic.cpp` | HC-SR04 ping, blocking `pulseIn`, mm conversion |
| ambient | `src/sensors/ambient.cpp` | DHT11 via SimpleDHT, checksum flag, x10 scaling |
| water level | `src/sensors/water_level.cpp` | One `analogRead` on A0 |
| analog environment | `src/sensors/analog_environment.cpp` | Thermistor A1, photoresistor A2, each mean of 4 reads (`:5-9`) |

Init order in `setup()` (`main.cpp:8-18`): boot counter, `alarm::begin()` (amber, buzzer
silent), `transport::begin(boot)` (Serial 115200), `sampler::begin(boot)`, then one
STATUS frame (`transport::status()`, binary build only).

## 3. Pin map

Single source: `include/config.h:17-21`. Cross-checked against
`docs/hardware/design.md` "Uno pin allocation": **no mismatch**.

| Pin | Signal | `config.h` | design.md |
|---|---|---|---|
| D2 | HC-SR04 ECHO (input) | `kUltrasonicEcho=2` | D2 ECHO |
| D3 | HC-SR04 TRIG (output) | `kUltrasonicTrig=3` | D3 TRIG |
| D4 | DHT data | `kAmbientData=4` | D4 |
| D5/D6/D7 | Green / amber / red LED | `kGreen/kAmber/kRed` | same |
| D8 | Buzzer via PN2222 (`tone()`) | `kBuzzer=8` | same |
| A0/A1/A2 | Water level / thermistor / LDR | `14/15/16` | same |
| D9-D12, A3 | Reserved (deferred stepper/IR, ADR-008) | not present | reserved |

Notes: the reserved pins exist only in `design.md`, not in `config.h`. `alarm::begin()`
(`alarm.cpp:16`) initialises pins by looping `kGreen..kBuzzer`, so it silently depends
on those four constants staying contiguous (5..8). `tone()` takes Timer 2 (framework
`Tone.cpp:93-122`: 328P uses timer 2), which disables PWM on D3 and D11 while active;
D3 is used only as plain digital, so this is fine as long as nobody `analogWrite`s D3.

## 4. Timing budget

All cadences are start-to-start gates using `uint32_t(now - last) >= interval`
(rollover-safe across the ~49.7 day `millis()` wrap).

| Task | Cadence | Where | Notes |
|---|---|---|---|
| Ultrasonic ping | 150 ms (`kUltrasonicIntervalMs`) | `ultrasonic.cpp:16` | HC-SR04 needs >= 60 ms between pings |
| DHT11 read | 2000 ms (`kAmbientIntervalMs`) | `ambient.cpp:18` | first read at t >= 2 s |
| Water/thermistor/LDR | once per report, at assembly | `sampler.cpp:42-44` | 1 + 4 + 4 = 9 ADC conversions |
| DATA report | 1000 ms (`kReportIntervalMs`) | `sampler.cpp:31` | `lastReport = now`, so period is 1000 ms plus loop latency, not phase-locked |
| STATUS | 1000 ms (`kStatusIntervalMs`) | `sampler.cpp:30` | also at boot and on GET_CONFIG; sent even when streaming is off |
| RX partial-frame timeout | 500 ms (`kRxTimeoutMs`) | `serial_protocol.cpp:57` | |
| Host-silence fallback | 3000 ms (`kHostTimeoutMs`) | `alarm.cpp:23` | |

### Blocking calls (worst case, from source)

| Call | Location | Worst case | Basis |
|---|---|---|---|
| `pulseIn(ECHO, HIGH, 25000)` | `ultrasonic.cpp:21` | 25 ms | One shared loop counter across the wait-for-idle, wait-for-start and measure phases (`wiring_pulse.S`, `--maxloops`), so the whole call is bounded by the timeout; the echo-start wait is deducted from the measurable width. Interrupts stay enabled. |
| Trigger pulse | `ultrasonic.cpp:18-19` | 12 us | `delayMicroseconds(2)` + `(10)` |
| DHT11 `sensor.read` | `ambient.cpp:21` | ~25 ms typical (arithmetic: `delay(20)` at `SimpleDHT.cpp:215` plus ~4-5 ms of 40 bits); **~520 ms** if the data line is stuck low | `levelTimeout = 500000` us (`SimpleDHT.h:65`, protected); `sample()` returns at the first stage that times out. Typical figure is an estimate, **unmeasured**. |
| 9 `analogRead` | `sampler.cpp:42-44` | ~1 ms (estimate: ~104 us each at the default prescaler) | **unmeasured** |
| `crc16` over <= 44 B | `serial_protocol.cpp:23-30` | bitwise, 8 shifts/byte; **unmeasured** | Runs once per built frame and once per complete candidate frame in RX |
| `Serial.write` | `serial_protocol.cpp:19` | none | guarded by `availableForWrite()` (`:15`); TX is interrupt-driven |
| CSV `Serial.print` chain | `serial_protocol.cpp:46-50` | blocks if the line does not fit the 64 B TX buffer | debug build only; a long line can exceed 63 B |

Worst normal loop iteration: ultrasonic (25 ms) + DHT (~25 ms) + analogs (~1 ms), about
51 ms when the two gates coincide (estimate, **unmeasured**). Fault case (DHT line held
low): ~545 ms. Consequences: the 1 Hz report and 150 ms ping are targets, not
measured jitter (requirement N09 is unmeasured on hardware); ACK latency is up to one
loop iteration; in the DHT fault case the host's 500 ms ACK timeout can expire.

UART RX during blocking: hardware RX buffer is 64 B (`HardwareSerial.h:53`), filled by
interrupt while blocked (5.56 ms to fill at 115200 8N1, 10 bits/byte = 11520 B/s). A
10-byte command takes 0.87 ms on the wire, and the host keeps one command in flight,
so this is safe for the current protocol. A new blocking call must state what it does
to this budget.

### 1 Hz report path

`loop()` -> `sampler::poll()` (`sampler.cpp:26`): capture `now` once (`:27`) ->
`ultrasonic::poll(now)` (may block <= 25 ms) -> `ambient::poll(now)` (may block) ->
STATUS if due (`:30`) -> if report due (`:31`): read snapshots, 9 ADC reads, fill
`Sample` (`:39-49`), `++sequence` (`:50`), `transport::send` if streaming (`:51`) ->
`frame()` builds a 36-byte DATA frame on the stack (`serial_protocol.cpp:13-20`) and
queues it. The return value of `send()` is ignored: a drop shows up to the host as a
sequence gap. Because `now` is captured before the blocking sensor calls,
`sample.timestamp` and `lastUpdate` can lag the real completion by up to the blocking
time (ultrasonic age reads 0 even though the echo returned up to ~25 ms after `now`).
TX time for a 36-byte frame at 115200: about 3.1 ms.

## 5. Resource budget (measured 2026-09-27, this session, build only)

Command: `platformio run --project-dir firmware -e uno -e uno_csv` (uno was cleaned and
rebuilt to surface warnings).

| Env | RAM (static) | Flash | Project warnings |
|---|---|---|---|
| `uno` (binary) | 394 B / 2048 (19.2%) | 7212 B / 32256 (22.4%) | none |
| `uno_csv` (`-DSENTINEL_CSV=1`) | 392 B (19.1%) | 7576 B (23.5%) | none |

Framework warnings only: four `-Wunused-parameter` in `cores/arduino/new.cpp`.
`uno` RAM = `.data` 78 + `.bss` 316 (avr-size). Largest symbols (avr-nm): `Serial`
157 B (includes 64 B RX + 64 B TX buffers), `rx` 47 B, `sample` 29 B, `SimpleDHT11`
object 11 B. Free for stack: 2048 - 394 = 1654 B; **stack high-water mark is
unmeasured** (requirement N01 is only half met). Largest project locals by
inspection: `frame()` buffer 47 B (`serial_protocol.cpp:14`), SimpleDHT `read2` data[40].
Flash headroom: 25044 B (`uno`).

## 6. Serial protocol implementation

Wire format and command semantics are owned by `docs/protocol/v1.md` and
`docs/decisions/ADR-009`. This section is what the firmware actually does.

- **Frame**: `A5 5A | ver | kind | len | payload | crc_lo crc_hi`. `kFrameMax` = 47
  (`serial_protocol.cpp:8`), derived from `kMaxPayload` 40 + 7. CRC-16/CCITT-FALSE,
  bitwise, over ver..payload (`:17`, `:23-30`).
- **RX buffer**: `rx[47]` (`:10`). At most `kRxBudget` (32) bytes are read per `poll()`
  (`:58-59`) so sampling is not starved. `if (used==sizeof(rx)) consume(1)` (`:60`) is a
  defensive overflow guard; the parser normally consumes a frame before the buffer fills.
- **Resync**: on a bad magic, version, length (> 40) or CRC, drop exactly one byte and
  rescan (`:62-69`); a wrong-version frame is discarded silently, with no ERROR. A false
  length can hold the parser for up to 47 bytes, but the rescan recovers a real frame
  embedded in the buffer. A partial frame is dropped after 500 ms without a byte (`:57`;
  only checked when `used != 0`; a single stray byte can sit until the next byte or
  the timeout).
- **Command dispatch** (`:70-83`): only 3-byte payloads (`id_lo, id_hi, value`) are
  commands. `SET_ALARM` value <= 3 sets the alarm, else ACK result 1; `CLEAR_ALARM` sets
  state 0; `START_STREAM`/`STOP_STREAM` toggle `enabled` (RAM only; default true, so
  streaming starts at boot before any command); `PING` and `GET_CONFIG` do nothing beyond
  the ACK (`GET_CONFIG` then sends STATUS); any other kind gets ACK result 2.
- **ACK** (`:81-82`): payload `{id_lo, id_hi, kind, result}`, sent for every 3-byte
  frame with a valid CRC, including result 1 and 2.
- **Heartbeat**: `alarm::heartbeat()` runs only when result == 0 (`:80`), so an
  invalid value or unknown kind does not keep the host "alive".
- **ERROR**: any valid-CRC frame whose length is not 3 gets ERROR code 3 (`:84-86`), with
  no ACK and no heartbeat.
- **TX**: `frame()` drops the frame (returns false) unless `availableForWrite() >=
  length+7` (`:15`); it never blocks. ACK, ERROR and STATUS results are ignored
  (silent loss, host retries). A dropped DATA frame is visible only as a sequence gap
  because `sequence` increments regardless (`sampler.cpp:50`). Max free TX space is 63 B
  (`HardwareSerial.cpp:201`, 64 B buffer): STATUS 17 + DATA 36 + ACK 11 = 64 > 63, and
  STATUS and DATA are always due in the same `poll()` (see defect 2), so a command
  handled in the same loop pass (especially `GET_CONFIG`, which adds another 17 B) can
  cause the DATA frame to be dropped. Margin under real traffic is **unmeasured**.
- **CSV build**: `status()` is a no-op and `send()` prints text `D,...` (`:35-41`, `:44-51`)
  using blocking `Serial.print`; ACK/ERROR frames are still binary and would interleave
  with text if a host sent commands, so the CSV build is read-only debug only.

## 7. Alarm state machine (as implemented, `src/actuators/alarm.cpp`)

State is one byte in RAM (`:4`): 0 NORMAL (green), 1 WARNING (amber), 2 FAULT (red +
buzzer `tone(D8, 2500 Hz)`), 3 UNKNOWN (amber). WARNING and UNKNOWN drive the same
LED, so they cannot be told apart from the device (`:9`). `set()` (`:6-14`) writes
all three LEDs and starts or stops the tone.

| Event | Result |
|---|---|
| Reset / power-up | state 3 (`:4`, `:19`); a FAULT is not persisted across reset |
| `SET_ALARM v`, v <= 3 | state = v, **directly, including over FAULT** |
| `SET_ALARM v`, v > 3 | ACK result 1, state unchanged, no heartbeat |
| `CLEAR_ALARM` | state 0, also over FAULT |
| Any valid non-error command | heartbeat: `lastHost = millis()` (`:21`) |
| `alarm::poll()`: `now - lastHost > 3000 ms` and state != 2 (`:23`) | state 3 (re-applied on every `loop()` while silent) |
| Host silent, state == 2 | stays FAULT indefinitely (buzzer keeps sounding) |

So the FAULT "latch" survives host silence only. It is not a latch against the host:
any `SET_ALARM 0..3` or `CLEAR_ALARM` replaces it, and the host sends `SET_ALARM(3)`
after each reconnect (`docs/protocol/v1.md:103-108`). `lastHost` starts at 0, and
`state` starts at 3, so boot behaves as "host never seen". This is a safety-relevant
behaviour: any change needs an ADR, a test plan and the user's hardware retest.

## 8. EEPROM boot counter

`main.cpp:10-13`: read u32 at address 0; `0xFFFFFFFF` (erased) -> 1, else +1;
`EEPROM.put`. `put` uses `update()` per byte (`EEPROM.h:137-140`), so only changed
bytes are written: byte 0 on every boot, byte 1 every 256 boots. Consequences: one
EEPROM cell is written on every reset (rated ~100k cycles, datasheet figure not
re-verified here), so a board that resets in a loop wears it; the four-byte
update is not atomic, so a power loss mid-write can leave a torn value; the ID is not a
unique identity. Do not use repeated resets as a stress test. Boot IDs 47 and 55
in the earlier captures are quoted from the role notes, **not verified** in this pass.

## 9. CSV vs binary builds

| | `uno` | `uno_csv` |
|---|---|---|
| Define | none | `-DSENTINEL_CSV=1` (`platformio.ini:12-14`) |
| DATA output | 36-byte binary frame | text `D,boot,seq,ts,dist,dist_age,water,therm,light,temp,hum,amb_age,flags` |
| STATUS | 17-byte frame at boot, 1 s, GET_CONFIG | none |
| Blocking on TX | never (drop) | `Serial.print` can block |
| RAM / flash | 394 / 7212 | 392 / 7576 |

`SENTINEL_CSV` code lives only in `serial_protocol.cpp` behind `#ifdef` and must not
change the binary build.

## 10. Invariants (flag violations)

1. No heap, no recursion, no unbounded loops; every wait is bounded and its worst case
   is written in section 4.
2. Elapsed time is rollover-safe (`uint32_t(now - last) >= interval`). All gates comply
   today.
3. Missing is flagged, never zero. Note: on failure the sensors keep the **last value**
   and clear the validity flag (`ultrasonic.cpp:22`, `ambient.cpp:22-26`); the age
   field carries the staleness. Consumers must not use the value when the flag is 0.
4. Parser and buffers bounded on both sides; a new frame kind needs bounds, an
   ACK/ERROR decision and an `api` contract update. `kProtocolVersion` and
   `kMaxPayload` must equal `python/sentinel/acquisition/protocol.py` (`VERSION = 1`,
   `MAX_PAYLOAD = 40`: match as of this pass).
5. Nothing blocks long enough to lose UART bytes (section 4).
6. Pin map lives only in `config.h` and agrees with `docs/hardware/design.md`.
7. CSV code stays behind `#ifdef`.
8. Alarm semantics change only with ADR + test plan + hardware retest.
9. `static_assert(sizeof(Sample) == 29)` (`types.h:12`) and
   `sizeof(Sample) <= kMaxPayload` (`serial_protocol.cpp:9`) guard the wire layout.

## 11. Watchpoint register (all unmeasured unless stated)

| # | Watchpoint | Status |
|---|---|---|
| W1 | `tone()` Timer 2 interrupt (2500 Hz toggling) may perturb `pulseIn` cycle counting while the buzzer sounds; `alarm::set(2)` also re-calls `tone()` on every repeated `SET_ALARM 2` | unmeasured |
| W2 | Ultrasonic echo dropouts (~38-39% invalid in the 1 h capture) are most likely physical; firmware cannot distinguish them; needs a logic-analyser/scope capture (hand to `hardware-bringup`) | unmeasured |
| W3 | Worst-case loop latency and report jitter (25 ms `pulseIn` + DHT + serial); requirement N09 | unmeasured |
| W4 | EEPROM wear from repeated resets | reasoned, no cycle count |
| W5 | `crc16` bitwise cost on target, including worst-case RX rescans (up to 32 B per poll) | unmeasured |
| W6 | Stack high-water mark (1654 B nominally free) | unmeasured |
| W7 | DHT stuck-line blocking (~520 ms) and its interaction with the host 500 ms ACK timeout | from source, unmeasured on hardware |
| W8 | TX-buffer margin when STATUS + DATA + ACK coincide | from source, unmeasured on hardware |
| W9 | ADC accuracy after channel switch with 10 k dividers (no dummy read before the 4-sample mean) | unmeasured |

## 12. Known defects

Firmware source is never edited by this role; apply and retest on hardware, unless noted fixed.

1. **Fixed 2026-09-27, not flashed.** STATUS and DATA no longer share a tick:
   `sampler.cpp` now inits `lastStatus = 500` (was 0, same as `lastReport`), so the
   two are staggered and a coincident ACK/`GET_CONFIG` STATUS can no longer overflow
   the 63 B TX budget and drop DATA. Rebuilt clean: `uno` 7,218 B flash / 394 B RAM
   (+6 B flash), `uno_csv` 7,582 B / 392 B (+6 B). **Not yet verified on hardware.**
2. **Fixed 2026-09-27, not flashed.** `alarm::poll()` no longer re-runs `set(3)`
   (four `digitalWrite`s plus `noTone()`) every loop once already idle: the guard is
   now `state!=2 && state!=3`. Behaviour-identical (still reaches state 3 exactly
   once per silence), just stops repeating the redundant work. **Not yet verified on
   hardware.**
3. **DHT11 read can block ~520 ms** (`ambient.cpp:21`; `SimpleDHT.h:65`
   `levelTimeout` 500 ms, protected). Not fixed: shortening the timeout risks the DHT
   never completing a read on the real part, so it needs bench tuning, not a blind
   edit. Fix: subclass to lower it, e.g.
   `struct Dht : SimpleDHT11 { using SimpleDHT11::SimpleDHT11; void limit(long us){levelTimeout=us;} };`
   with `limit(1000)`, or back off after repeated failures.
4. **`tone()` re-invoked on every repeated `SET_ALARM 2`** (`alarm.cpp:12`): can restart
   the tone. Not fixed (lower priority than #2; same "needs retest" caveat). Fix:
   only call it on a transition into state 2.
5. **`alarm::begin()` relies on contiguous pins 5..8** (`alarm.cpp:16`). Not fixed.
   Fix: add `static_assert(kBuzzer == kGreen + 3 && kRed == kGreen + 2 && kAmber == kGreen + 1)`.
6. **Timestamps precede blocking sensor work** (`sampler.cpp:27`, `ultrasonic.cpp:25`):
   `timestamp`/age understate by the blocking time (<= ~50 ms). Cosmetic at 1 Hz, not fixed.
7. Stale `.pio/libdeps/uno_edge` (OneWire) exists in the git-ignored build cache from a
   removed env; no effect on builds, not fixed.

## 13. How to build (never flash)

From the repo root in PowerShell:

```powershell
$env:PLATFORMIO_CORE_DIR = Join-Path (Get-Location) '.pio'
.\.venv\Scripts\python.exe -m platformio run --project-dir firmware -e uno -e uno_csv
```

The toolchain is cached under `.pio/`; a fresh download needs network, so ask first.
Project sources must be clean under `-Wall -Wextra`; the `new.cpp` framework warnings
are not project warnings. Forbidden for this role: `--target upload`,
`device monitor`, opening any COM port, `sentinel acquire/csv`. Uploading is the user's
step, followed by the hardware checks in `docs/failures/verification-matrix.md`.

## 14. Not verified in this pass

Anything on real hardware (no board access by rule); loop timing and jitter; stack
depth; `crc16` cycles; DHT typical read time; ADC conversion time; EEPROM endurance
figure; the boot IDs 47/55 in captures; that the `wiring_pulse.S` phase accounting
matches real echo timing (read from source only).

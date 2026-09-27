# Hardware bring-up log

Owner: the `hardware-bringup` role. This is a dated log of what was wired, measured
and observed on the SentinelDAQ rig, with the next physical step. It does not replace
[`design.md`](design.md) (BOM, pins, power) or [ADR-011](../decisions/ADR-011-calibration-approach.md)
(calibration approach); where the log contradicts them it says so.

Rules for this log:

- Every number comes from a file (read-only query of `sentinel.sqlite` and the raw
  Parquet) or was told to us by the person at the bench (marked **reported**).
- Everything recorded so far is **uncalibrated bring-up data**. Raw counts and
  millimetres are the only trustworthy columns; do not quote any percentage or the
  thermistor/DHT temperatures as measurements (ADR-011).
- The role that writes this log never touches the board or a COM port. The person at
  the bench runs the commands below and reports back. **Wiring changes are made with
  power off (USB unplugged).**
- `flags` is a bit mask: `1` = distance valid, `2` = DHT valid, `4` = DHT checksum
  error (`firmware/src/acquisition/sampler.cpp`; `docs/protocol/v1.md` calls the
  first "bit 0", the firmware comment calls it "Bit 1"; this log always uses the mask
  value).
- One sample per second. The distance flag is the outcome of the **most recent 150 ms
  ping** at the moment the sample is assembled (`ultrasonic.cpp` keeps the last good
  reading and only clears `valid`), so the 1 Hz valid rate is a per-ping success rate
  seen once a second. While the flag is clear, `distance_mm` is a stale value and
  `distance_age_ms` is the time since the last good ping (saturates at 65,535).
- Times are UTC as recorded. Local time (MYT, UTC+8) is an assumption about where the
  rig was used and is only given in brackets.

---

### 2026-09-27 - Read-only analysis of every physical run (no hardware touched)

#### Setup (what the files say, and what nobody has recorded)

- Firmware `0.1.0`, protocol 1, plain `uno` build, 115200 baud, machine `tank-1`.
  All nine run records are condition `NORMAL`, `simulated = 0`, placeholder
  calibration (empty 1000 mm, full 50 mm, dry 200, wet 800).
- `operator_metadata` is the unfilled `run-template.json` for the 09-19/20 runs
  (`fe263795`, `1ba3ff02`, `0ef6e2a5`, `1a285efb`, `a8c0ebf2`), empty `{}` for the
  09-23 runs, and for `30284a5b` it is a leftover **motor-bench template** (`motor_model`,
  `shunt_ohms_measured`, `guard_and_disconnect_check`), i.e. from the pre-pivot BOM.
- Not recorded anywhere: tank, HC-SR04 height/angle/mount, probe depth, module part
  numbers and voltages, DHT marking, thermistor part, divider resistor values, any tape
  measurement, any photograph, operator notes for any run (`operator_notes` is empty
  in all of them). So no observation below can be tied to a known physical state.

#### Runs (per run, not pooled)

Source: `data/physical` (`sentinel.sqlite`, `raw/`) and `data/physical_check`. Rows were
sorted by `host_timestamp_ns` inside each run. "Valid" = `flags & 1`. IQR = 25th to
75th percentile of valid readings. Ranges are min-max of the raw column.

| Run (8 chars) | Start UTC (MYT) | Wall / samples | Status | Boot | Distance valid | Longest invalid streak | Valid distance median (IQR), range | Water raw median (range) | Thermistor raw median (range) | Light raw median (range) |
|---|---|---|---|---|---|---|---|---|---|---|
| `30284a5b` | 09-19 04:28 (12:28) | 190 s / 189 | INTERRUPTED | 37 | 100% (189/189) | 0 | 2212 mm (5), 2200-2221 | 9 (8-11) | 475 (473-479) | 226 (215-242) |
| `1ba3ff02` | 09-19 04:32 (12:32) | 486 s / 485 | INTERRUPTED | 38 | 100% (485/485) | 0 | 2212 mm (5), 820-2221 | 590 (6-672) | 473 (461-485) | 195 (187-643) |
| `fe263795` | 09-19 04:40 (12:40) | 542 s / 540 | INTERRUPTED | 40 | 99.4% (537/540) | 2 | 2207 mm (77), 2128-2224 | 581 (573-589) | 466 (461-473) | 200 (196-219) |
| `0ef6e2a5` | 09-19 04:49 (12:49) | 653 s / no raw | INTERRUPTED (reconciled) | - | - | - | raw rows lost (killed; see failures) | - | - | - |
| `1a285efb` | 09-19 23:39 (07:39 09-20) | 372 s / 0 | INTERRUPTED | - | no frame decoded | - | - | - | - | - |
| `a8c0ebf2` | 09-19 23:46 (07:46 09-20) | 18,158 s / 18,155 | INTERRUPTED | 47 | 99.99% (18,154/18,155) | 1 | 379 mm (18), 32-524 | 7 (5-15) | 479 (464-483) | 147 (110-602) |
| `fb76dfcd` | 09-23 02:58 (10:58) | 0 s / no raw | INTERRUPTED (reconciled) | - | - | - | - | - | - | - |
| `e05e4450` | 09-23 02:58 (10:58) | 20 s / 19 | COMPLETE | 53 | 100% (19/19) | 0 | 166 mm (3), 114-566 | 7 (6-57) | 534 (534-535) | 139 (139-141) |
| `48b1ce36` | 09-23 03:01 (11:01) | 3,600 s / 3,598 | COMPLETE | 55 | **62.0% (2,231/3,598)** | **204 samples (3 min 24 s)** | 164 mm (6), 42-788 | 496 (112-698) | 549 (530-559) | 145 (101-247) |

Continuity, jitter, DHT (per run):

| Run | Boot changes mid-run | Sequence gaps | `timestamp_ms` step (median / max) | Host receive step p1-p99 | DHT valid | DHT checksum-error samples | DHT readings (whole units) | `ambient_age_ms` |
|---|---|---|---|---|---|---|---|---|
| `30284a5b` | 0 | 0 | 1000 / 1021 ms | 975-1025 ms | 99.5% | 0 | 44-45 C, 31-35 %RH | 0-1026, alternates ~24 / ~1024 |
| `1ba3ff02` | 0 | 0 | 1000 / 1021 ms | 970-1029 ms | 98.6% | 6 (1.2%) | 36-45 C (45 at start, 37 at end), 31-46 %RH | max 3025 |
| `fe263795` | 0 | 0 | 1000 / 1023 ms | 975-1026 ms | 98.7% | 6 (1.1%) | 36 C flat, 46-47 %RH | max 3025 |
| `a8c0ebf2` | 0 | 0 | 1000 / 1022 ms | 986-1014 ms | 98.5% | 280 (1.5%) | 33-35 C, 57-62 %RH | max 3027 |
| `e05e4450` | 0 | 0 | 1000 / 1000 ms | 975-1025 ms | 94.7% (1 sample before the first read) | 0 | 27 C, 50-51 %RH | 0-1000 |
| `48b1ce36` | 0 | 0 | 1000 / 1021 ms | 986-1014 ms | 99.1% | 30 (0.8%) | 27 C flat, 47-50 %RH | max 3025 |

Notes on the continuity numbers:

- Zero sequence gaps and zero mid-run boot changes in all six runs that have raw data
  (about 5 h + 1 h + four short runs). The Uno did **not** reset or brown out spontaneously
  during any recording. The firmware boot counter is an EEPROM counter that increments on
  every reset, including the DTR reset when a serial port is opened: boot IDs 37, 38, 40,
  47, 53, 55 across runs are consistent with one reset per port open, but 40 to 47 and 47 to 53
  skip several boots that have no stored run (uploads, `csv`, device queries or failed
  opens are the obvious candidates; the data cannot say which).
- Distance readings sit on a ~4-5 mm comb (2207/2208/2211/2212/2216/2220 mm at 2.2 m;
  154/160/164/169/173 mm at 16 cm), not a smooth spread. Resolution is coarser than the
  0.17 mm the firmware arithmetic implies. Do not read the IQR (3-18 mm) as noise floor
  below about 5 mm. Cause not established (module-internal timing is one possibility).
- DHT: every failed DHT read in every run is a checksum error (the only DHT-invalid
  samples that are not checksum errors are the single sample before the first read).
  Values are whole numbers (multiples of 10 in deci-units) and plausible as DHT11
  output (a DHT22 read through the DHT11 decoder would give humidity near 0-3 and
  temperature 0-1, not 31-62 %RH and 27-45 C). This supports, but does not confirm, a DHT11.
  1-1.5% of reads fail: ordinary for a DHT11, cost is one held sample.
- `timestamp_ms` steps are 1000 ms with occasional +21-23 ms slips (1 to 3 per run; in
  the 1 h run 3 of 3,597). That is the largest main-loop stall observed (`pulseIn` timeout
  is 25 ms; a DHT read also blocks ~20 ms). The "DHT read is bounded, ~ms" line in the risk
  register is optimistic; the data cannot separate DHT from `pulseIn` as the source.

#### The ultrasonic dropouts are one event pattern in one run, not a general rate

Only `48b1ce36` has meaningful dropouts (1,367 samples, 38.0%; the summary's 1,398 also
counts stale-distance and DHT-invalid samples). The other runs: 0%, 0%, 0.6% (3 samples,
`fe263795` at t = 37, 44, 45 s), 0.006% (1 sample at t = 14 s of the 5 h run, during
what looks like handling), 0%.

`48b1ce36`, per minute (valid rate; median of valid readings; water raw median):

| Minute | Valid | Distance (valid) | Water raw | What the numbers show |
|---|---|---|---|---|
| 0 | 60% | median 200, range 42-732 | 457 (112-505) | distance jumping 42-732 mm, water rising from 112 to 505 within the minute: something was being moved/placed |
| 1 | 32% | 176 (160-645) | 455 (265-513) | still disturbed |
| 2-3 | **0%** | none | 475-478, flat | no echo at all for 120 s while the water reading is steady |
| 4-6 | 98-100% | 160 (min 5-6 range 154-160; min 4 also has 45-607 outliers) | 470-477 | clean, IQR under 5 mm |
| 7-11 | 57%, 13%, 8%, 20%, 52% | mostly none; most valid returns in minutes 7-11 are 676-788 mm (about 30 samples) rather than 160 | 479-493, creeping up | echo lost while the water reading is smooth; valid returns are from a far object, not from 160 mm |
| 12-39 | **100% every minute** (1,680/1,680 samples, 0 invalid) | 154-173 mm, median 164 | 493 rising to 510 (+17 in 28 min) | fully healthy, IQR 3-9 mm |
| 40 | 97% | 164, then 359 | 510 with min 209, max 596 | water raw jumps: first change since minute 12 |
| 41 | 53% | 194 (83-638) | 590 (533-698) | water peaks at 698 (highest in the run) |
| 42-46 | 0-5% | 1 valid reading in min 42 and one in min 45 | 373-581, then 185-240 | echo essentially gone; water raw falls to ~180 |
| 47-59 | 0-47%, mean about 15% | valid ones are almost all exactly 189 mm (103 samples) or 176 mm (19 samples), plus a few at 473-631 (including 564/565 mm, the same value at different times) | 191 falling smoothly to 154 by minute 56, then 156-173 | the surface now reads 25 mm farther (164 to 189 mm) and the water reading has dropped by two thirds |

Pattern statistics for `48b1ce36`:

- Dropouts are bursts, not scattered pings: P(invalid | previous invalid) = 0.926,
  P(invalid | previous valid) = 0.046. 102 invalid streaks, 42 of them 1-3 samples (70
  samples in total), 31 of them 10 samples or longer accounting for 1,132 of the 1,367
  invalid samples. Longest 204 samples. Median `distance_age_ms` of invalid samples is
  8.1 s, 9.7% of them are at the 65,535 ms saturation (dropout longer than 65 s).
- There is no duration or warm-up trend: the run starts bad (minutes 0-11), is perfect for
  28 minutes, then goes bad again from minute 41 to the end.
- The clock-time hypothesis does not hold: the 5 h run `a8c0ebf2` (07:46-12:48 MYT) covers
  the same time of day as `48b1ce36` (11:01-12:01 MYT) with 1 invalid sample in 18,155.
- Not correlated with the DHT read: invalid rate is 0.383 when the DHT was read within
  the last 100 ms vs 0.377 otherwise.
- Correlated with events that move `water_level_raw`: the last, longest bad stretch starts
  at the minute the water raw jumps 510 to 698 and then settles at ~170. The first bad
  stretch coincides with the water raw ramp from 112 to 505. It is **not** explained by
  water alone: minutes 2-3 (0% valid) and 8-11 have a steady water reading.
- Valid-distance median is 164 mm in the healthy stretch and 189 mm after the disturbance
  (25 mm farther, valid rate 5-38%), while the water raw is lower. Water and distance
  changes are in the direction of a lower water level or a moved probe/sensor, but the
  data do not say which.

`a8c0ebf2` (5 h), for contrast: valid 99.99%, distance median 379 mm but it is not a fixed
mount: median 469 mm in the first 15 min, 408 (15-30 min), 387, then 374-379 from about
the first hour to about 4.5 h, then ~350 mm for the last 20 min (per-15-min medians). Light
raw was about 560 (median 534) for the first 15 min, then ~120-150. About 3% of
samples (567, in 381 short groups from about 77 min onward) read 157-176 mm, one or two
samples at a time, i.e. a nearer reflector occasionally winning inside the beam. Water raw
stayed 5-8 (median 7) apart from a brief excursion up to 15 near t = 2,013-2,016 s.

`1ba3ff02` and `fe263795` (2.2 m runs, 09-19): 100% and 99.4% valid. `fe263795` alternates
between two distinct distances, 2131/2135/2139 mm and 2207/2212/2216 mm (77 mm apart),
in blocks of 106, 116, 61, 65, 61, 23, 61, 47 samples (the high blocks are 61 s three times
running). `1ba3ff02` shows the same lower level (2131-2143 mm) from t = 196 s onward, after
isolated 949 mm and 820 mm readings at t = 108 s and 143 s. `1ba3ff02` also has light raw
600-643 for at least 20 s (samples 74-93 onward, up from ~195) and a 17/42/42 blip in the water raw at t = 99-101 s.

#### Water probe, per run

- `30284a5b`: 8-11, ending 8. `a8c0ebf2`: 5-8 for 5 h (median 7; 15 max). `e05e4450`: 57/46 in the
  first seconds falling to 7 by t = 8 s and staying (6-7). These are the dry reading: 5-15
  counts, steady to +-1, and the `a8c0ebf2` floor does not follow `light_raw` (560 to 120)
  so there is no evidence of channel cross-talk lifting or lowering it.
- `1ba3ff02`: 8 until t = 148 s, then a step to ~640 within a few samples and a decay to
  581 by the end (one 17/42/42 blip earlier at t = 99-101 s). `fe263795`: 573-589
  throughout (median 581, drifting by no more than +-8).
- `48b1ce36`: 112 rising to ~505 in the first ~4 min, creeping 493 to 510 through minute
  40 (+17 in 28 min), then the excursion and a smooth decline to 154 by minute 56.
- Observed dry floor 5-15; observed wet 470-698 at unrecorded depths. The placeholders
  (dry 200, wet 800) do not bracket this: everything under 200 (the whole `a8c0ebf2`
  run, the last 15 minutes of `48b1ce36`) clips to 0%, and 800 is above every reading
  ever seen.
- Water raw changes by hand-moved amounts (steps of 20-600 counts in seconds) show the
  channel responds to the probe being inserted/removed, so wiring and the ADC path work.

#### Thermistor, light, DHT (per run, all unreferenced)

- Thermistor raw medians 475, 473, 466 (09-19 morning), 479 (09-20 night), 534 (09-23 20 s),
  549 (09-23 1 h). With the placeholder NTC constants (10 kohm series, 10 kohm at 25 C,
  beta 3950) that is 28.3, 28.4, 29.1, 27.9, 23.0, 21.7 C. Ranges are tight (4-24 counts).
- The DHT reads warmer than the thermistor by: +16.7 C (`30284a5b`, 45 vs 28.3), about +11 C
  and shrinking (`1ba3ff02`, 45 falling to 37), +6.9 C (`fe263795`, 36 vs 29.1), +5.1 C
  (`a8c0ebf2`, 33 vs 27.9), +4.0 C (`e05e4450`, 27 vs 23.0), +5.3 C (`48b1ce36`, 27 vs 21.7).
  A settled offset of about +4 to +7 C in the last three datasets, plus a warm start
  (45 C, decaying over ~20 min, while the thermistor did not follow) on 09-19.
  Neither sensor has a reference; the DHT11 is specified +-2 C and the thermistor constants are
  placeholders, so the data cannot say which is wrong or whether the two are simply
  in different places (near the Uno regulator, in sun, in a hand).
- Light raw: 110-250 in most sessions, about 560 for the first ~15 min of the 5 h run,
  600-643 for 20 s in `1ba3ff02`. Uncalibrated relative light; the divider orientation
  is not recorded.

---

#### Conclusions

Ranked most likely physical causes. "Data can" / "data cannot" per item; nothing here is
a measurement of the cause.

**(a) Ultrasonic dropouts (one 1 h run; concentrated in minutes 0-11 and 41-59)**

1. **Target or geometry disturbed by handling or by a level change (aim, tilt, obstruction
   in the beam).** Confidence moderate-high that it is physical/geometric rather than
   electrical. Data can: the same sensor and wiring returned 100% valid for 28 minutes
   (1,680 samples) and 99.99% for 5 h; the bursts start where the rig was evidently being
   worked on (distance jumping 42-732 mm at the start, water raw jumping at minute 40);
   when the echo is lost, the few valid samples are real, repeatable echoes from other
   objects (564-565 mm at different times; 189 mm 103 times), which an electrical fault would
   not produce. Data cannot: whether the sensor was bumped, the tank/probe moved, the level
   fell 25 mm, or a hand or object was in the beam; and minutes 2-3 (0%) have no water event.
2. **Marginal echo from a slightly tilted or off-axis sensor over a specular (flat, still
   or rippling) water surface**, so a small change in level or angle moves the reflection off
   the receiver. Confidence low-moderate. Data can: valid rate collapsed after the reading
   changed from 164 to 189 mm and while valid returns were mostly fixed values (189, 176).
   Data cannot: the sensor's angle, surface state (foam, ripple after filling), or the tank
   walls and rim relative to the ~15 degree beam (a nearer object intermittently winning, as in the 5 h run's 157-176 mm blips).
3. **Droplet, splash or condensation on a transducer face.** Confidence low. It would be
   persistent after the disturbance and would clear when dry, which fits the 18-minute bad
   stretch but equally fits cause 1 or 2. Data cannot tell.
4. **Intermittent contact (jumper/breadboard/ECHO, TRIG, GND, VCC) when the rig was handled.**
   Confidence low-moderate. Bursts at handling times fit it; repeated identical far returns
   during a dropout (564/565 mm, twice) argue the module was working. Data cannot tell.
5. **Electrical or firmware causes: 5 V droop, no common GND, DHT read interference, timeout,
   warm-up, time of day, TRIG/ECHO swapped, target inside the 2 cm minimum.** Confidence low:
   the data argue against each. 28 minutes and 5 h of near-perfect readings rule out chronic
   droop, missing GND, a wrong pin map and the 25 ms timeout; invalid rate is the same whether
   or not the DHT was just read; there is no time or duration trend; steady readings never
   go below ~150 mm (the few 32-45 mm values happened while the rig was being handled).

**(b) Water probe reads only its dry floor**

1. **Probe not in the water (in air, or the level never reached its sensing area).**
   Confidence high. Data can: the same channel steps between 6-9 and 500-670 when the
   probe is handled (`e05e4450` t = 8 s, `1ba3ff02` t = 148 s, `48b1ce36` minutes 0-4); a
   floor of 5-15, steady to +-1 counts, for 5 h is what a resistive module reads dry.
   Data cannot: whether the probe was left out of the tank or the tank level stayed below it
   (in the 5 h run the ultrasonic distance moved from ~470 to ~350 mm), or how deep any
   wet reading was.
2. **Low sensitivity to immersion depth and slow drift/polarisation or early corrosion of the
   resistive traces.** Confidence low-moderate, not established. Data can: in water the raw
   creeps +17 in 28 min and decays 185 to 154 in 15 minutes (level change or trace effect).
   Data cannot: any trace state, or which of level, polarisation or wetted length moved it.
   Whether the 5 V feed should be switched only during sampling is a design change to raise
   with the owner, not an assumption made here.
3. **Wrong module voltage, floating input, ADC channel cross-talk.** Confidence low. Wet
   readings are in a sensible range, the floor is steady, and it does not track `light_raw`. Data cannot
   verify the module's voltage rating (not recorded).

**(c) ~2.2 m readings (`30284a5b`, `1ba3ff02`, `fe263795`)**

1. **The sensor was aimed at a distant room surface (wall, ceiling, floor or furniture), not
   the tank surface.** Confidence high. Data can: 100% / 100% / 99.4% valid, IQR 5 mm in the
   first two runs, a hard stable target; the water probe was wet in `1ba3ff02` (after t =
   148 s) and `fe263795` while the distance stayed at 2.2 m; 2.2 m is well inside the 25 ms
   / ~4.3 m timeout. The failures log also carries an operator report of mounting/aiming
   (**reported**). Data cannot: which surface, or the tape distance.
2. **Two surfaces or a moving target at 2.135 m and 2.212 m** (77 mm apart, alternating in
   blocks, three 61-second blocks in `fe263795`). Confidence moderate that it is a physical
   target change (a fan, curtain, door, person, or an edge of a ceiling fixture), since a
   3.5% jump is not a speed-of-sound effect. Data cannot identify it.
3. Not supported: an electrical fault (a wrong TRIG/ECHO or a bad pin gives no or
   random echoes, not a stable 2.2 m), or a temperature error (the thermistor moves 1-2 C
   across these runs).

#### Unknown (needs the bench, not more analysis)

- Whether any HC-SR04 reading is accurate: no tape reference exists.
- What the sensor was aimed at in each run, and its height/angle.
- The actual dry and wet water-probe counts at a stated depth; module voltage rating; probe condition.
- DHT marking (DHT11 vs DHT22 vs a look-alike), thermistor part, divider resistor values, which of DHT and thermistor is closer to true temperature.
- Whether the 09-19 DHT warm start was a hot spot near the DHT.
- What happened at 03:42 UTC on 09-23 (minute 41 of `48b1ce36`) and in minutes 0-11.
- USB unplug, reset, kill, missing-sensor and alarm behaviour on hardware (verification-matrix rows below).
- Firmware/binary hash and the exact rig wiring (no schematic or photo exists).

#### Contradictions and gaps between this analysis, `design.md`, `config.h` and other docs

1. `design.md` Uno pin table and `config.h` agree (D2 ECHO, D3 TRIG, D4 DHT, D5-D7 LEDs, D8 buzzer,
   A0-A2 = 14-16). No contradiction on pins.
2. `design.md` BOM has **no buzzer row** (only the PN2222 that "drives the buzzer"), while `config.h`
   sets a **passive piezo at 2500 Hz via `tone()`** (`kBuzzerHz`). The design does not say the
   part is passive or that a static HIGH is silent. A passive piezo draws milliamps and does not
   strictly need the transistor. Design owner should add the part.
3. `design.md` says the DHT is "assumed DHT11 by default, confirm". The data are consistent with DHT11
   output and inconsistent with a DHT22 read through the DHT11 decoder, but the marking is still
   unconfirmed. (Support, not a contradiction.)
4. `design.md` thermistor divider is 5 V - resistor - NTC - GND and `pipeline.py` uses `R = 10k * raw / (1023 - raw)`.
   These match. But the data disagree with the DHT by +4 to +17 C, so at least one of the two is
   not a temperature measurement yet.
5. `design.md` says the HC-SR04 is mounted "above the tank, facing the liquid surface". Three
   runs show it was not (2.2 m). The design is the target, not the recorded state.
6. `design.md` and ADR-011 present 200/800 as placeholders; the data now show they sit outside
   the observed range (dry 5-15; wet 470-698 at unknown depth). `level_water_pct` is 0% for any
   count under 200 and can never reach 100%. ADR-011 quotes "medians of 496-590 in others"; those
   medians hide a 6-672 range and a 505 to 154 change within single runs (`1ba3ff02`, `48b1ce36`).
7. The risk register says DHT reads are bounded at "~ms"; the data show loop stalls to 21-23 ms
   (DHT start signal ~20 ms and `pulseIn` up to 25 ms both fit).
8. `docs/failures/README.md` and the role brief say the 5 h run "read a median 379 mm" as if a fixed
   mount. It moved from ~470 to ~350 mm over the run while the probe read dry throughout; the median hides that.
9. `docs/protocol/v1.md` calls the distance-valid flag "bit 0" (mask 1); the `sampler.cpp` comment
   calls it "Bit 1". Same mask, two numberings.
10. Run `30284a5b` carries motor-bench `operator_metadata` from the pre-pivot BOM (ADR-008).
    `data/` is read-only for this role; it should be noted, not edited.
11. `firmware/.pio/libdeps/uno_edge/OneWire` exists although `design.md` says "no OneWire" and
    `platformio.ini` does not list it: a stale library folder from the old DS18B20 design
    (`platformio.ini` defines `uno` and `uno_csv`, not `uno_edge`). Harmless, but it is
    not the current build.

---

#### Safety (read before the steps below)

- **Liquid and a USB-powered Uno.** Keep any water in a container that cannot tip, on a
  tray, lower than and to one side of the Uno/breadboard, with the probe leads long enough that a
  drip runs away from the board. No mains, no immersion of anything except the probe's sensing
  area. Keep a towel at hand. If anything is splashed near the board: unplug USB first, then dry.
- **Wiring changes are made with USB unplugged.** Re-check polarity and continuity before re-plugging.
- **Module voltage.** Before the module goes on Uno 5 V, read its marking or datasheet. Some
  water-level and DHT modules are 3.3 V only (a 5 V feed can damage them). If the
  rating is unknown, do not power it from 5 V until identified; say so in the log.
- **Buzzer transistor.** A PN2222A and a P2N2222A in TO-92 have **opposite pin orders** (EBC vs
  CBE). Check the printed part number against its datasheet and confirm the base-emitter junction
  with the multimeter diode test before power. Size the base resistor against the datasheet and the
  buzzer current, not by guess.
- **LEDs** each need their 1 kohm series resistor (about 3 mA at 5 V).
- **Never** short, overvolt, wet or stress a component to make a fault appear. "Missing sensor"
  tests below disconnect, they do not damage.
- The water-probe module is powered continuously from 5 V while immersed; cheap resistive probes
  corrode. Keep soak times short during calibration, dry and rinse between repetitions, and record the
  total time immersed.

---

#### Next 5 physical steps (priority order)

Setup for all runs: use a **new data directory** (`data/bringup`) so the old evidence is not mixed.
Find the port each time (it can change after a replug):

```powershell
cd C:\Users\nadee\Documents\smart_hardware_edge_ai
.\.venv\Scripts\python.exe -m serial.tools.list_ports
```

One metadata file per run (copy the template, fill it in, put the measured values in):

```powershell
Copy-Item docs\experiments\run-template.json docs\experiments\bringup-2026-09-28-us-300mm.json
notepad docs\experiments\bringup-2026-09-28-us-300mm.json
```

Fill `sensor_mounting`, `distance_empty_mm_measured` etc. as measured, `operator`, and set
`electrical_safety_check` to `DONE` after step 1. Do not touch or move anything while a run is in
progress; if you must, write the wall-clock time and what you touched into `--notes`.

**Step 1 - Power off: identify parts, check voltage and wiring (no acquire yet).**
USB unplugged. Photograph the whole rig and each module (front and back). Write down in the
metadata file: HC-SR04 marking (and whether it is a 3-pin or 5-pin clone), water-level module
marking and rated voltage, DHT marking (blue DHT11 or white DHT22, any printed name), thermistor
marking, the fixed resistor in each divider (measure it out of circuit with the multimeter), PN2222
part number and orientation, buzzer type (passive/active). Continuity-check TRIG D3, ECHO D2,
all module GNDs to Uno GND, and each VCC to 5 V. Then plug USB, and with the multimeter measure
5 V at the HC-SR04 VCC-GND and the water-module VCC-GND (expect 4.75-5.25 V). Good looks like: every
module is rated for 5 V (or unpowered until proven), continuity everywhere, no shorts, 5 V rail steady.
Record: a table of parts and voltages in this log, photos in `docs/hardware/` (file names in the log entry).

**Step 2 - HC-SR04 on its own, aimed at a flat target at tape-measured distances (no water).**
Power off and remove everything except the HC-SR04 from the signal side you can (the other channels will
report floating values; ignore them). Mount the sensor rigidly (clamp, not hand held), face straight at a
flat rigid board (at least 30 cm square, perpendicular to the beam, nothing else in front of the sensor
within 1 m). Tape from the sensor **face** to the board: 200, 300, 500, 1000 mm. Run each for 120 s
without touching anything:

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/bringup acquire --port COM5 --seconds 120 --condition NORMAL --notes "HC-SR04 only, flat board, tape 300 mm, rigid clamp" --metadata-json docs\experiments\bringup-2026-09-28-us-300mm.json
```

(Replace `COM5`, the tape value and the metadata file name for each distance.) Check the newest run:

```powershell
$rid = (Get-ChildItem data\bringup\*-summary.json | Sort-Object LastWriteTime | Select-Object -Last 1).Name.Substring(0,36)
.\.venv\Scripts\python.exe -c "import sys,glob,numpy as np,pyarrow as pa,pyarrow.parquet as pq; rid=sys.argv[1]; t=pa.concat_tables([pq.read_table(f) for f in glob.glob('data/bringup/raw/'+rid+'/*.parquet')]).to_pydict(); f=np.array(t['flags']); d=np.array(t['distance_mm']); v=(f&1)>0; print('samples',len(f),'valid',round(float(v.mean()),4),'median',np.median(d[v]),'p25',np.percentile(d[v],25),'p75',np.percentile(d[v],75))" $rid
```

Good looks like: valid at least 99% and no invalid streak over 2 samples at every distance; median
within about 2% of the tape plus the face offset (the firmware fixes 343 m/s; at 28 C the real speed
is ~348 m/s, so readings run about 1.5% short); IQR at most ~6 mm. If it passes, the sensor, wiring and
power are fine and the field problem is aim or target. If it fails at every distance, swap the sensor
for a spare (power off) and repeat before touching anything else. Record: run ids, tape values, valid
rate, median, IQR per distance, in a table in this log.

**Step 3 - Water probe: dry and wet counts per ADR-011, away from the board.**
Probe wired to A0 and nothing near the Uno that can wet it: a tall cup on a tray, the Uno and
breadboard on the other side of the bench with the probe leads pulled taut and away from
the board. Mark the intended immersion depth on the probe with tape. Sequence, each block with a
separate `acquire` run of at least 90 s (need 60 s of settled data each): dry in air; immersed to the mark;
lift out and dry with a towel; repeat until you have three dry and three wet runs. Note the water
temperature and the wall-clock time each block starts. Command (change the notes each time):

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/bringup acquire --port COM5 --seconds 120 --condition NORMAL --notes "water probe DRY rep 1, water 26 C" --metadata-json docs\experiments\bringup-2026-09-28-probe.json
```

Good looks like: dry median 5-15 (past captures), wet median several hundred, stable within +-10 counts
over the last 60 s of each block, the three repetitions within +-15 counts of each other, and the
median wet at the mark clearly above dry. Then pass the medians as `--water-dry-raw` and `--water-wet-raw` on
later runs and write them in `water_dry_raw_measured`/`water_wet_raw_measured`. If wet drifts by
more than about 30 counts in 2 minutes, or the three repetitions disagree, note it as probe
instability (possible corrosion) and raise the 5 V-always-on question with the design owner.

**Step 4 - Aim and mount at the tank, with a tape reference, then a level change.**
Power off. Mount the HC-SR04 rigidly (bolt/clamp/bracket) above the tank facing straight down. Check
with a small spirit level or a plumb line. Clear anything within 15 degrees of the beam (tank rim,
walls, bracket): at the ~16-19 cm distance seen in the 09-23 run the tank wall must be more
than about 5 cm from the axis, at 38 cm about 10 cm. Tape-measure the sensor face to the water at the
current level and at a second level (add or remove a known amount, e.g. 20 mm of depth). Run 10 minutes at
each level, hands off:

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/bringup acquire --port COM5 --seconds 600 --condition NORMAL --distance-empty-mm <tape_empty_mm> --distance-full-mm <tape_full_mm> --water-dry-raw <dry_median> --water-wet-raw <wet_median> --notes "tank, HC-SR04 rigid, level A, tape <mm>" --metadata-json docs\experiments\bringup-2026-09-28-tank-A.json
```

(The `--distance-*` and `--water-*` values may be the measured ones from steps 2 and 3, or leave them at the
defaults if you are still measuring, but say which in the notes.) Good looks like: valid at least 99% for
the whole 10 minutes, median within ~2% of the tape, and moving the level by 20 mm moves the median by ~20 mm the
right way (level up gives a smaller distance) while the water raw rises. If the valid rate falls below 95%: tilt
the sensor by a small known angle to see whether it recovers, wipe the transducer faces dry, and note
foam/ripples on the surface; a 5 minute wait after filling before recording avoids ripples.

**Step 5 - Thermistor and DHT against a reference thermometer, and DHT identification.**
Place a reference thermometer (a decent digital one, note its accuracy) touching the thermistor and
within 2 cm of the DHT, away from the Uno's regulator and the buzzer, out of sun and air currents. Let
it settle for 15 minutes, then run 10 minutes:

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/bringup acquire --port COM5 --seconds 600 --condition NORMAL --notes "temp reference: thermometer 26.4 C at start, 26.5 C at end" --metadata-json docs\experiments\bringup-2026-09-28-temp.json
```

Good looks like: thermistor raw stable within ~3 counts, DHT temperature within +-2 C of the reference
(DHT11 spec), and the thermistor within ~2 C once the code owner has updated the placeholder constants
from the datasheet or your measured resistance. Also measure the thermistor's resistance with a multimeter (unpowered, out of circuit)
at the reference temperature, and record the DHT marking. If the DHT still reads +4 to +7 C above the
reference, move it away from the Uno and re-test to check for a hot spot. Record: reference, DHT median, thermistor raw median and
resistance, all with the instrument name.

After steps 1-5 update this log and hand the run ids back to the hardware-bringup role: it will do the read-only
numbers, compare to the tape values, and update ADR-011's inputs (the owner of the ADR edits it).

---

#### How to record results (every step)

For each run add a `### YYYY-MM-DD - <what was done>` entry with: setup (mounting, wiring,
instruments, tape values), the exact command run, run id(s) and data directory
(`data/bringup`), the observations with numbers (from a file, or **reported** if from your own
notes/instruments), a conclusion, and the next step. A number you did not see in a file or that
the operator did not report is not written down. Photos go under `docs/hardware/` and are named
in the entry. Keep failed and inconvenient runs; note why they were excluded rather than deleting.

---

#### Verification-matrix rows that need the rig (controlled tests, checklist)

Do these after step 1 (wiring verified) and before any dataset run. Use the whole rig connected as in
`design.md`, water away from the board. Each test is its own `acquire` run into `data/bringup` so
the evidence has a run id. Write down wall-clock times to the second for every action (phone clock).
Current (2026-09-27) status of all rows: **not yet done**.

Expected firmware behaviour to compare against (from `alarm.cpp`, `runner.py`, `main.cpp`):
UNKNOWN (state 3) is amber D6 and the boot default; NORMAL green D5; WARNING amber D6; FAULT red D7
plus a 2500 Hz `tone()` on D8. Non-FAULT states fall to UNKNOWN 3 s after the last host command;
FAULT is kept on host silence, but any later `SET_ALARM`/`CLEAR_ALARM`, including the reconnect
`SET_ALARM(3)`, overrides it. The host declares data lost after 2 s of silence and the boot counter
increments on every reset.

- [ ] **V1. USB unplug/replug** (row: "USB unplug/replug").
  Setup: rig connected, `acquire --seconds 600` running in a visible window.
  Steps: (1) note time T0 at which streaming looks healthy. (2) At about T0+60 s unplug the USB cable
  at the **PC end** (note the time). (3) Watch the console and LEDs for 30 s. (4) Replug (note the time).
  (5) Look at Device Manager (Ports) for the COM number; note whether it is the same as before. (6) Watch for
  30 s. (7) Repeat once unplugging at the **Uno end**. Ctrl-C at the end.
  Expected: host declares loss within ~2 s and state UNKNOWN; LEDs amber within 3 s (or unchanged if
  FAULT); on replug the Uno reboots (boot +1, sequence back to 1); if the COM port is the same number the host
  reopens, reconfigures and resumes streaming with a new session and cleared windows; no stale command is replayed
  (check the ACK count and `command_failures` in the summary). If the number changes, the running process
  cannot follow it: that is a finding (write it down, do not treat it as a pass).
  Log: times, console text, run id, the run's `-summary.json` (`reconnections`, `resets`, `sequence_gaps`,
  `command_failures`, `parser_errors`), and the boot and sequence values either side of the gap (I read them
  from the Parquet). Done when both unplug points are observed with times and the expected/observed columns are filled in.
- [ ] **V2. Arduino reset** (row: "Arduino reset").
  Setup: same. Steps: with streaming healthy press the Uno's reset button for about a second, three times at least 60 s
  apart (note each time).
  Expected: LEDs go amber (boot state UNKNOWN); the boot ID increases by 1 each time and `sequence` restarts at 1; the host
  drops its window (state UNKNOWN), reconfigures (GET_CONFIG, START_STREAM, SET_ALARM) and streaming resumes within a few
  seconds; the gap in `host_timestamp_ns` is a few seconds; `resets` in the summary counts them. Log: reset times,
  boot IDs before/after, time to first valid sample, LED behaviour. Done when three resets are logged with these values.
- [ ] **V3. Stop Python** (row: "Stop Python").
  Two separate runs. (a) **Ctrl-C** in the acquire window at a known time. Expected: run ends `INTERRUPTED`, the
  summary exists, all rows on disk; the Uno keeps its state until 3 s of host silence, then amber (or stays red if it
  was FAULT). (b) **Hard kill**: find the PID (`Get-Process python | Select Id,StartTime,Path`, pick the one whose
  path is the repo's `.venv` and whose start time matches this run) and end only that process
  (`Stop-Process -Id <pid>`), at a known time. Expected: the run stays `RUNNING` with no summary; up to about 30 s of raw rows
  is lost (raw rows now flush every 30 s or 1,600 rows), earlier data present; LED goes amber within ~3 s. Afterwards
  `.\.venv\Scripts\python.exe -m sentinel --data data/bringup audit` lists it under `unfinished_runs`; that is
  read-only. `reconcile` may then be run once by you (it rewrites the row, so only after you have saved the audit
  output). Log: kill time, last sample time in the data, the audit output, the LED time. Done when both are logged.
- [ ] **V4. Missing sensor** (row: "Missing sensor"). USB unplugged for every wiring change.
  One run of 120 s per case, notes stating the case, reconnect afterwards:
  (a) **HC-SR04**: remove only its VCC wire (module unpowered, signal wires left). Expected: distance-valid flag clear (mask 1) from the
  start, no invented distances. (b) **HC-SR04 fully disconnected** (all four wires). Expected: no echo, flag clear. **This case may
  instead produce spurious "valid" readings**, because the firmware does not pull ECHO up or down (a floating input on D2). If it does,
  that is a real finding, not a wiring hazard: record how many, and how the values look. (c) **DHT data wire off**. Expected: DHT valid
  flag (mask 2) clear, `ambient_age_ms` climbing, pipeline ambient values empty after 4 s; checksum bit may or may not be set.
  (d) **Water probe signal wire off A0** (A0 floating). There is no validity flag for analog channels, so expect arbitrary
  or drifting counts (this is the known limitation "plain analog reads are always valid"): record the values and how they
  differ from a dry probe (5-15). (e) Thermistor or photoresistor divider tap off: same, floating values. Log: per case the flag rates, values, and what
  the host displayed. Done when each case is run and the difference between "invalid flagged" and "silently wrong" is stated per sensor.
- [ ] **V5. Physical alarm outputs** (row: "Physical alarm" outputs; latency stays separate and open).
  Steps and expectations: (1) Power-up and after a reset with **no host**: amber D6 only, buzzer silent.
  (2) Host running with steady healthy data: record which LED is lit (NORMAL should be green D5 only) and which state the console
  shows; if the host never reaches NORMAL because there is no trained model or windows do not fill, say so. (3) Stop the host: the
  LED changes to amber within ~3 s (time it). (4) Buzzer and red D7: FAULT is the only state that sounds the buzzer; **do not create
  a fault by damaging or shorting anything**. The safe, currently available path is to let the host raise WARNING/FAULT
  from real data only if a safe condition (e.g. covering the tank or lowering the level by hand) legitimately does so. If that is
  not reachable, mark the WARNING/FAULT/buzzer part **not exercisable** and ask the firmware owner for a bench-only SET_ALARM tool. Do
  not claim a pass without seeing the red LED and hearing the tone. (5) While the buzzer sounds, check the PN2222 is not getting hot (touch
  test after a few seconds, USB still connected, nothing wet nearby). (6) If FAULT is ever reached, stop Python (V3a) and confirm red and the tone stay
  on (the "FAULT is kept on host silence" quirk); then reconnect and note that the host's `SET_ALARM(3)` overrides it. Log: LED per state,
  buzzer heard or not, times, part orientation photo. Done when every state is observed or explicitly marked not reachable with the reason.
- [ ] **V6. Alarm latency** stays **open**. It needs a shared trigger (logic analyser on the sample event and the LED/buzzer pin). Do not
  report a latency figure from `host_timestamp_ns` or `timestamp_ms` alone.

To mark a row done in `docs/failures/verification-matrix.md` the owner of that file needs: the date, the run ids and data
directory, the exact steps and times, expected vs observed, the summary/audit output, and any surprise. Add those to a new
dated entry in this log first; the matrix row then points here.

# Hardware design proposal

> Pivoted from the original ADXL345/INA219/DS18B20/motor BOM to the tank/
> environmental sensor set actually on hand — see
> [ADR-008](../decisions/ADR-008-sensor-set-pivot.md). No physical acceptance
> from the old BOM carries over; every item below is unverified against real
> hardware until it's actually wired and exercised.

## Initial BOM

| Item | Qty | Selection / verification |
|---|---|---|
| Arduino Uno R3 / ATmega328P | 1 | Existing; identify board and USB bridge |
| USB data cable | 1 | Connector matching board; data-capable |
| HC-SR04 ultrasonic sensor | 1 | Mount above the tank, facing the liquid surface; confirm 3.3–5V logic compatibility with the Uno (most HC-SR04 modules are 5V-native) |
| Water-level detection module (resistive/analog) | 1 | Obtain exact ADC dry/wet range by measurement — the `--water-dry-raw`/`--water-wet-raw` CLI defaults (200/800) are placeholders |
| DHT temperature/humidity module | 1 | Confirm DHT11 vs DHT22 from the part's markings; firmware defaults to DHT11 scaling (`ambient.cpp`) — swap to `SimpleDHT22` and drop the ×10 whole-unit scaling if it's a DHT22 |
| Thermistor (NTC) | 1 | Confirm rated resistance/beta from the part; `pipeline.py`'s NTC beta conversion uses placeholder constants (10kΩ series, 10kΩ @25°C, β=3950) pending the datasheet |
| Photoresistor (LDR) | 1 | Any fixed-resistor voltage divider; reported as an uncalibrated relative percentage, not lux |
| PN2222 NPN transistor | 1 | Drives the buzzer from D8 (base resistor from D8, buzzer/load on collector, emitter to GND) — base resistor value depends on the buzzer's rated current, size it against the PN2222's datasheet |
| Green / amber / red LEDs | 1 each | Individual 1 kΩ starting resistors; check brightness/current |
| Fixed resistors for both analog dividers (thermistor, photoresistor) | 2 | Values depend on the specific parts; size from their datasheets |
| Breadboard, jumpers | as needed | |
| Multimeter | 1 | Required for polarity, continuity and rail checks |

**Deferred, not wired this revision:** a stepper motor and an IR receiver module
are also on hand but have no role in the tank/environmental design. Reserved
pins are set aside for them (see below) but no firmware or wiring exists yet —
see ADR-008 for the reasoning.

No purchase price or stock availability is claimed. Keep any liquid away from
the Uno, breadboard and USB connection; route the water-level probe's leads so
a drip cannot bridge onto logic-level wiring.

## Uno pin allocation

| Uno | Signal | Direction / notes |
|---|---|---|
| D0/D1 | USB UART RX/TX | Reserve; no external peripheral |
| D2 | HC-SR04 ECHO | Sensor → Uno |
| D3 | HC-SR04 TRIG | Uno → sensor |
| D4 | DHT data | Bidirectional, single-wire; same slot the old DS18B20 used |
| D5 | Green LED | Output through resistor |
| D6 | Amber LED | Output through resistor |
| D7 | Red LED | Output through resistor |
| D8 | Buzzer, via PN2222 | Output; base resistor from D8 to the PN2222 base |
| D9–D12 | Reserved for a future stepper (ULN2003 driver + 28BYJ-48, 4 pins) | **Deferred — not wired** |
| D13 | Free | Shares the onboard LED; avoid using as a sensor input |
| A0 | Water-level module | Analog in |
| A1 | Thermistor divider midpoint | Analog in |
| A2 | Photoresistor divider midpoint | Analog in |
| A3 | Reserved for a future IR receiver (read via `digitalRead`, sidesteps the D2/D3 interrupt contention an interrupt-based IR library would want) | **Deferred — not wired** |
| A4/A5 | Free | I2C-capable if ever needed; unused for now |

No SPI, no I2C, no OneWire in this design — everything is a plain digital pulse
(HC-SR04), a single-wire digital read (DHT), or a plain `analogRead()`.

## Power and wiring concept

```text
PC USB ----------------> Uno logic power (5V)
Uno 5V -----------------> HC-SR04 VCC (most modules are 5V-native)
Uno 5V -----------------> DHT VCC (check the specific module's rated voltage)
Uno 5V -----------------> water-level module VCC
Uno 5V -- divider R --> thermistor -- GND      (A1 taps the midpoint)
Uno 5V -- divider R --> photoresistor -- GND   (A2 taps the midpoint)
Uno GND ----------------> all module GNDs, common reference
D8 -- base resistor --> PN2222 base; buzzer/load on collector; PN2222 emitter to GND
```

Verify each module's actual rated supply voltage before wiring to Uno 5V — some
water-level and DHT modules are 3.3V-only. Keep the water-level probe's wiring
and any liquid well away from the breadboard's logic connections.

## Before power-on

Record board/module part numbers and photos; review each module's datasheet;
measure rails and polarity with everything disconnected; then connect one
sensor at a time with power off, checking continuity before applying power.
Record the final wiring schematic once all modules are confirmed.

## Primary references

- [Uno documentation](https://docs.arduino.cc/hardware/uno-rev3/)
- [Uno pinout](https://content.arduino.cc/assets/Pinout-UNOrev3_latest.pdf)
- [HC-SR04 datasheet](https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf)
- [DHT11 datasheet](https://www.mouser.com/datasheet/2/758/DHT11-Technical-Data-Sheet-Translated-Version-1143054.pdf)

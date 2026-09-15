# Hardware design proposal

## Initial BOM

| Item | Qty | Selection / verification |
|---|---|---|
| Arduino Uno R3 / ATmega328P | 1 | Existing; identify board and USB bridge |
| USB data cable | 1 | Connector matching board; data-capable |
| ADXL345 breakout | 1 | Obtain exact schematic and supply/I/O ratings |
| SPI-capable voltage translator | as needed | Direction-controlled, suitable for selected SPI clock; avoid generic slow I2C shifters |
| Regulated 3.3 V source / decoupling | as needed | Check breakout and Uno rail budget |
| INA219 breakout | 1 | Shunt resistance, tolerance, power and connector ratings must cover motor stall current |
| DS18B20, externally powered | 1 | Verify package pinout/probe wire mapping |
| 4.7 kohm 1-Wire pull-up | 1 | Initial value; validate with cable capacitance |
| Green / amber / red LEDs | 1 each | Individual 1 kohm starting resistors; check brightness/current |
| Active buzzer + transistor driver | 1 | Rated supply/current, base/gate resistor and off-state bias; diode for inductive load |
| 6–12 V DC motor and guarded fixture | 1 | Confirm stall current, mounting and mechanical containment |
| External current-limited motor supply | 1 | Voltage/current matched to motor |
| Fuse, disconnect, suppression, terminal wiring | as needed | Size from motor current and wiring; disconnect accessible |
| Breadboard, short jumpers, rigid sensor mount | as needed | Keep motor-current wiring off breadboard |
| Multimeter | 1 | Required for polarity, continuity and rail checks |
| Logic analyzer / oscilloscope | optional | Later timing, bus and power-noise measurements |

No purchase price or stock availability is claimed. Phase 1 only needs Uno,
USB cable, ADXL345, verified power/translation, wiring and multimeter. Keep motor
disconnected during static sensor tests.

## Proposed Uno pin allocation

| Uno | Signal | Direction / notes |
|---|---|---|
| D0/D1 | USB UART RX/TX | Reserve; no external peripheral |
| D2 | ADXL345 INT1 | Sensor → Uno; verify high-level threshold or translate |
| D3 | Reserved | Future RPM interrupt |
| D4 | DS18B20 DQ | Bidirectional; pull up to verified logic supply |
| D5 | Green LED | Output through resistor |
| D6 | Amber LED | Output through resistor |
| D7 | Red LED | Output through resistor |
| D8 | Buzzer driver | Output; hardware bias keeps driver off at reset |
| D9 | Reserved timing marker | Future analyzer measurement |
| D10 | ADXL345 CS | Uno → sensor through required translation; idle high |
| D11 | ADXL345 SDI/MOSI | Uno → sensor through required translation |
| D12 | ADXL345 SDO/MISO | Sensor → Uno; check guaranteed logic thresholds |
| D13 | ADXL345 SCLK | Uno → sensor through required translation; shared onboard LED |
| A4/SDA | INA219 SDA | Same physical bus as dedicated SDA header |
| A5/SCL | INA219 SCL | Same physical bus as dedicated SCL header |
| A0–A3 | Reserved | No initial analog acquisition |

No external LED uses D13, because it is SPI clock. Document final breakout pin
labels before attaching wires; this table is a net allocation, not an approved
breakout-specific schematic.

## Power and wiring concept

```text
PC USB ------------------> Uno logic power
verified low-voltage rail -> ADXL345 supply
Uno SPI <-> voltage interface <-> ADXL345
Uno logic rail -----------> INA219 logic supply (verify breakout pull-ups)
Uno 5 V ------------------> DS18B20 VDD (external-power mode)

motor PSU + -> fuse -> accessible disconnect -> INA219 VIN+ -> VIN- -> motor +
motor - --------------------------------------------------------> PSU -
PSU - ---- common reference/star point ---- Uno GND / sensor grounds
```

Do not connect the motor supply positive to Uno 5 V or power the motor from Uno.
Route motor return current directly to its supply, away from sensor ground paths.
USB ground joins the circuit; verify grounding before combining grounded bench
equipment. Add motor suppression appropriate to the final drive topology; no PWM
driver or motor control is included initially.

The bare ADXL345 uses a 2.0–3.6 V supply. A breakout accepting 5 V power does not
necessarily tolerate 5 V SPI inputs. Verify CS/SCLK/MOSI level translation and
MISO/INT logic margin against both devices' guaranteed thresholds. Keep wiring
short; select SPI mode/clock from the datasheet during Phase 1.

INA219 bus range is 0–26 V, but this does not establish module current capacity.
Check shunt heating using I²R, shunt measurement range, motor transients, connectors
and traces. For DS18B20, verify actual package pinout; probe wire colors are not
reliable pin specifications. Give each LED its own resistor. Drive buzzer through
a rated transistor rather than assuming GPIO can supply its current.

## Before power-on

Record board/module part numbers and photos; review schematics; measure rails and
polarity with sensor disconnected; inspect grounds and shorts; then connect the
sensor with power off. Record the final wiring schematic after modules are known.
No imbalance weights, loosened running fixtures or hand obstruction are authorized
by this preliminary design. Develop guarded, rated fault experiments in Phase 7.

## Primary references

- [Uno documentation](https://docs.arduino.cc/hardware/uno-rev3/)
- [Uno pinout](https://content.arduino.cc/assets/Pinout-UNOrev3_latest.pdf)
- [ADXL345 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/adxl345.pdf)
- [INA219 specifications](https://www.ti.com/product/INA219)
- [DS18B20 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ds18b20.pdf)

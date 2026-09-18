# ADR-008 — Pivot the sensor set from motor condition monitoring to tank/environmental monitoring

Status: accepted following user confirmation that the ADXL345/INA219/DS18B20/
DC-motor BOM assumed by ADR-001–007 does not match the hardware actually on
hand: an HC-SR04 ultrasonic sensor, an analog water-level module, a DHT temp/
humidity module, a thermistor, a photoresistor, a PN2222 transistor, a stepper
motor and an IR receiver module.

## Decision

Repurpose the project into an environmental/tank monitoring system. HC-SR04 and
the water-level module become two independent, cross-checking tank-level
sensors; DHT, thermistor and photoresistor become ambient/environmental
sensors; the PN2222 drives the existing buzzer alarm output. The stepper motor
and IR receiver module are explicitly **deferred** — pins are reserved for them
(D9–D12, A3; see hardware/design.md) but no firmware or wiring exists for
either in this revision.

This replaces, rather than extends, the prior BOM: no SPI, I2C or OneWire
remains in the design (supersedes ADR-002). The wire protocol's `Sample`
struct, the DSP feature set (no more FFT — slow-signal mean/slope/range/std
plus a two-sensor agreement feature), the ML condition vocabulary (NORMAL,
LOW_WATER, OVERFLOW, RAPID_DRAIN, SENSOR_MISMATCH, ENVIRONMENTAL_ANOMALY) and
the dashboard/report charts are all rewritten accordingly. Sampling drops from
an 800 Hz vibration waveform to one assembled report per second, since nothing
in the new sensor set needs or supports a high-rate stream.

## Consequences

None of the physical acceptance recorded — or rather, never yet recorded,
per ADR-007 — against the old BOM carries over. Every phase-1-through-4
acceptance criterion in PHASE-STATUS.md must be re-earned against the new
sensors: the water-level module's dry/wet ADC range, the thermistor's actual
resistance/beta, the DHT variant's exact scaling (DHT11 vs DHT22), and the
tank's real empty/full sensor distance are all unmeasured placeholders in
`pipeline.py`/`simulator.py`/`docs/hardware/design.md` until wired and tested.
Simulation-only development continues per ADR-007's existing policy — this ADR
changes *what* is being simulated, not the simulation-first discipline itself.

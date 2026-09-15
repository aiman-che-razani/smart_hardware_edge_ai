# SentinelDAQ — Arduino-Based Intelligent Condition Monitoring System

Act as a senior embedded systems, electronics, signal-processing, data-engineering, machine-learning, and backend engineer.

I want you to help me design and build a complete portfolio engineering project called:

**SentinelDAQ — Arduino-Based Intelligent Condition Monitoring System**

This must be treated as a real engineering system, not a toy Arduino tutorial or generic machine-learning demo.

I am building the project myself and want to understand every layer. Therefore:

* Explain important engineering decisions.
* Build incrementally.
* Do not generate the entire system at once.
* Do not introduce unnecessary enterprise infrastructure.
* Prefer simple, testable architectures.
* Do not hide complexity behind large frameworks when implementing the underlying engineering concept would be educational.
* Do not fabricate benchmark results.
* Clearly distinguish assumptions from measured results.
* Write production-quality, modular code.
* Include tests where appropriate.
* Document important design decisions.
* Stop at the end of each major phase and give me explicit instructions for testing it before proceeding.

---

# 1. PROJECT OBJECTIVE

Build an end-to-end machine condition-monitoring system using an existing **Arduino Uno** as the embedded data-acquisition device.

The system will monitor a small physical machine such as a:

* DC motor
* fan
* small pump
* similar rotating test rig

The initial system architecture is:

Physical Machine
→ Sensors
→ Arduino Uno
→ USB Serial
→ Python DAQ
→ Signal Processing
→ Feature Engineering
→ Machine Learning
→ Storage/API
→ Dashboard

There must also be a return control path:

ML Decision
→ Python
→ USB Serial
→ Arduino Uno
→ LED/Buzzer

The Arduino will NOT initially run the ML model.

Machine-learning inference will run on the Windows PC.

An optional final experiment will investigate whether a tiny classifier can later run directly on the Arduino Uno.

---

# 2. ENGINEERING GOALS

The finished project should demonstrate practical ability across:

* electronics engineering
* sensor interfacing
* embedded C/C++
* Arduino/ATmega328P
* deterministic data acquisition
* SPI
* I²C
* 1-Wire
* UART/USB serial
* communication protocols
* signal processing
* vibration analysis
* Python
* data engineering
* experimental design
* machine learning
* anomaly detection
* real-time inference
* SQLite/PostgreSQL
* FastAPI
* dashboard development
* testing
* benchmarking
* system integration

This project will eventually be presented as a professional engineering case study on my portfolio website.

---

# 3. HARDWARE CONSTRAINT

The embedded controller is:

**Arduino Uno / ATmega328P**

Assume approximately:

* 16 MHz CPU
* 32 KB flash
* 2 KB SRAM
* 10-bit ADC
* limited serial bandwidth
* limited processing capability

Design around these limitations instead of pretending they do not exist.

Memory usage, sampling performance, communication bandwidth and timing must eventually be measured.

---

# 4. RECOMMENDED V1 HARDWARE

Design around:

## Controller

Arduino Uno.

## Vibration

ADXL345 3-axis accelerometer.

Prefer SPI for high-rate vibration acquisition.

Verify voltage compatibility of the specific breakout board before assuming direct 5 V Uno interfacing.

## Current

INA219 current/power monitor over I²C.

## Temperature

DS18B20 temperature sensor using 1-Wire.

## Physical machine

6–12 V brushed DC motor with a safe fan, disk or similar rotating fixture.

The motor must have an external power supply.

Do NOT power the motor directly from the Arduino.

## Indicators

Use:

* green LED — NORMAL
* amber LED — WARNING
* red LED — FAULT
* active buzzer — serious alarm

Python must eventually be able to control these through USB commands.

---

# 5. TARGET SAMPLING ARCHITECTURE

Start with approximately:

ADXL345:
800 Hz target

INA219:
approximately 20–50 Hz

DS18B20:
approximately 1 Hz

Do not force all sensors to operate at the same rate.

The firmware should implement appropriate scheduling for sensors operating at different frequencies.

Measure the actual achievable sampling rates rather than assuming the configured rate is achieved.

---

# 6. FIRMWARE ARCHITECTURE

Do NOT put the complete firmware into one large `.ino` file.

Prefer PlatformIO and structured C++.

Use approximately:

firmware/
platformio.ini

```
include/
    config.h
    protocol.h
    types.h

src/
    main.cpp

    sensors/
        accelerometer.cpp
        accelerometer.h
        current.cpp
        current.h
        temperature.cpp
        temperature.h

    acquisition/
        sampler.cpp
        sampler.h

    filters/
        filters.cpp
        filters.h

    communication/
        serial_protocol.cpp
        serial_protocol.h

    actuators/
        alarm.cpp
        alarm.h
```

The embedded system should handle:

* sensor initialization
* sensor health checking
* deterministic acquisition
* sample sequence numbers
* device timestamps
* small buffers
* serial transmission
* command reception
* acknowledgements
* malformed commands
* hardware alarm states
* diagnostic/status reporting

Avoid dynamic memory allocation where practical.

Be conscious of the Uno's 2 KB SRAM.

---

# 7. SERIAL COMMUNICATION

Implement the communication protocol progressively.

## Development Protocol V0

Start with human-readable CSV so the complete acquisition chain can be debugged easily.

Example concept:

D,sequence,timestamp_us,ax,ay,az,current,temp

Do not blindly copy this format if a better field arrangement is justified.

## Production Protocol V1

After acquisition is stable, implement a compact binary framed protocol.

Design something approximately like:

MAGIC
VERSION
MESSAGE_TYPE
PAYLOAD_LENGTH
PAYLOAD
CRC16
END/FRAME CONTROL

Define message types for at least:

DATA
STATUS
ACK
ERROR

SET_ALARM
CLEAR_ALARM
START_STREAM
STOP_STREAM
PING
GET_CONFIG

Sensor packets should contain at least:

* sequence number
* device timestamp
* acceleration X
* acceleration Y
* acceleration Z
* current
* temperature
* status flags

Prefer compact integer/raw representations over ASCII floating point where appropriate.

Python will convert raw values into engineering units.

The protocol must support detection of:

* corrupted frames
* incomplete frames
* malformed frames
* unknown packet types
* sequence gaps
* dropped samples
* Arduino resets

Commands from Python should contain command IDs where appropriate.

Arduino should acknowledge commands.

Document the protocol formally.

---

# 8. PYTHON DAQ

Create a modular Python application.

Suggested structure:

python/
sentinel/

```
    acquisition/
        serial_reader.py
        parser.py
        reconnect.py

    processing/
        filters.py
        windows.py
        fft.py
        features.py

    ml/
        train.py
        evaluate.py
        inference.py
        models/

    storage/
        database.py
        repositories.py

    api/
        main.py

    config.py
```

The DAQ must eventually support:

* serial-port connection
* configurable baud rate
* continuous acquisition
* packet parsing
* CRC validation
* sequence validation
* host timestamping
* device timestamping
* dropped-sample detection
* buffering
* reconnection
* Arduino restart detection
* corrupted/incomplete message recovery
* logging
* clean shutdown
* bidirectional commands

Keep acquisition separate from signal processing and ML.

---

# 9. STORAGE

Do NOT start with unnecessary infrastructure.

For V1 use:

**Parquet + SQLite**

Use Parquet for high-volume experimental sensor measurements.

Use SQLite for:

* experiments
* metadata
* predictions
* events
* model information

Later allow migration to PostgreSQL when the backend is deployed.

Design schemas for:

## experiment_run

Include fields such as:

run_id
machine_id
started_at
ended_at
condition
fault_type
fault_severity
motor_setting
operator_notes
firmware_version
protocol_version
sampling_rate

## raw_measurement

Include:

host timestamp
device timestamp
sequence
run_id
acceleration XYZ
current
temperature
status flags

## feature_window

Include calculated signal features.

## prediction

Include:

model version
predicted state
probability/anomaly score
inference latency

## event

Include:

event start
event end
state
severity
probability
alarm state

Design appropriate primary keys and indexes.

---

# 10. SIGNAL PROCESSING

Condition monitoring, especially vibration analysis, is central to this project.

Implement signal-processing functions independently and test them.

Investigate:

* detrending
* DC removal
* filtering
* windowing
* Hann window
* RMS
* peak-to-peak
* standard deviation
* variance
* skewness
* kurtosis
* crest factor

Implement frequency-domain analysis using FFT.

Extract features such as:

* dominant frequency
* dominant amplitude
* spectral energy
* spectral centroid
* frequency-band energy
* harmonic relationships

Explain the physical meaning of important features.

Do not simply generate features because a library provides them.

For every major feature, explain what machine behaviour it may capture.

For example:

RMS:
overall vibration energy

Kurtosis:
impulsive behaviour

Crest factor:
large peaks relative to RMS

Frequency components:
periodic mechanical behaviour

Eventually investigate shaft-speed/order-based analysis if RPM measurement is added.

---

# 11. WINDOWING

Start by investigating approximately:

800 Hz vibration sampling

1-second windows

50% overlap

Do not treat these numbers as permanently correct.

Experiment with window length and overlap.

Document the trade-offs between:

* frequency resolution
* temporal resolution
* detection latency
* computational cost

---

# 12. EXPERIMENTAL DATASET

I want to create my own physical dataset.

Do NOT substitute a Kaggle dataset unless it is used only for secondary comparison.

Design controlled experimental runs representing conditions such as:

NORMAL

IMBALANCE_LOW

IMBALANCE_HIGH

LOOSE_MOUNT

PARTIAL_OBSTRUCTION

INCREASED_LOAD

SPEED_VARIATION

Only propose fault simulations that are mechanically and electrically safe.

Every experiment must receive a unique run ID.

Store metadata describing exactly how the experiment was performed.

Target multiple independent runs per condition rather than one long recording.

For example, eventually aim for approximately 10–20 independent runs for major conditions if practical.

Each run may contain approximately 60–120 seconds of measurements.

Do not assume these quantities are optimal; refine them from experimental results.

---

# 13. PREVENT DATA LEAKAGE

This is a strict requirement.

Consecutive windows from the same physical experiment are highly correlated.

Therefore NEVER randomly distribute windows from the same experimental run across training and test sets.

Split datasets by:

**run_id**

Use techniques such as:

* GroupShuffleSplit
* GroupKFold
* StratifiedGroupKFold where appropriate

All windows generated from a particular experimental run must remain in the same partition.

Maintain:

TRAIN

VALIDATION

TEST

The final test set should remain untouched during model development.

Explain any potential source of leakage before training models.

---

# 14. MACHINE-LEARNING DEVELOPMENT

Use a model ladder rather than immediately selecting the most sophisticated algorithm.

Evaluate approximately:

Level 0:
engineering thresholds

Level 1:
logistic regression

Level 2:
decision tree

Level 3:
random forest

Level 4:
Isolation Forest

Level 5:
XGBoost where justified

For supervised models evaluate:

* confusion matrix
* accuracy where meaningful
* precision
* recall
* F1
* per-class metrics
* ROC-AUC where appropriate
* PR-AUC where appropriate

Operational metrics are especially important:

* fault recall
* false-positive rate
* false alarms/hour
* missed faults
* inference latency

Do not automatically choose the model with the highest raw accuracy.

Compare:

* predictive performance
* false alarms
* interpretability
* inference latency
* model size
* robustness
* operational behaviour

---

# 15. REAL-TIME INFERENCE

Once a model is selected, integrate it into the live DAQ pipeline.

Pipeline:

serial measurements
→ buffer
→ signal window
→ preprocessing
→ feature extraction
→ model inference
→ state machine

Output:

NORMAL
WARNING
FAULT

Include:

* probability where supported
* anomaly score where supported
* timestamp
* model version

Do NOT activate FAULT based on a single unstable prediction.

Implement persistence and hysteresis.

For example, conceptually:

NORMAL → WARNING → FAULT

and require several consecutive high-risk windows before entering FAULT.

Require sustained recovery before clearing FAULT.

Make thresholds configurable.

---

# 16. BIDIRECTIONAL CONTROL

When Python enters FAULT:

Python
→ SET_ALARM
→ Arduino
→ red LED/buzzer

Arduino must ACK the command.

When the fault clears:

Python
→ CLEAR_ALARM
→ Arduino
→ alarm cleared

Test communication failure cases.

For example:

* command lost
* ACK lost
* Arduino reset
* serial cable disconnected
* duplicate command

Design sensible idempotent behaviour where possible.

---

# 17. BACKEND

After the core engineering pipeline works, create a lightweight FastAPI backend.

Potential endpoints:

GET /health

GET /machines

GET /measurements

GET /features

GET /predictions

GET /events

GET /experiments

GET /system/status

Potential streaming endpoint:

WebSocket /live

Do not implement authentication, distributed systems or microservices in early versions unless they become necessary.

---

# 18. DASHBOARD

Create a professional machine-condition-monitoring dashboard.

For V1 prefer:

**Plotly Dash**

Later, if useful for my personal portfolio:

**Next.js/React + FastAPI**

The dashboard should eventually display:

## Machine health

NORMAL / WARNING / FAULT

## Anomaly probability

Current ML probability/score.

## Live vibration

Time-domain waveform.

## FFT

Live/recent vibration frequency spectrum.

## Current

Motor current.

## Temperature

Motor temperature.

## DAQ health

* measured sampling frequency
* serial status
* dropped samples
* packet errors

## Historical trends

Display sensor and feature trends.

## Event history

Display detected WARNING/FAULT events.

## Experiment Explorer

Allow comparison between experimental runs such as:

NORMAL vs IMBALANCE

including waveform and FFT comparison.

The UI should look like an engineering monitoring system rather than a generic admin dashboard.

---

# 19. ENGINEERING BENCHMARKS

This project must contain measured engineering results.

Eventually measure:

## Embedded/DAQ

configured sampling frequency
actual sampling frequency
sampling error
sampling jitter
serial throughput
packet rate
dropped samples
CRC failures
Arduino SRAM usage
Arduino flash usage

## PC pipeline

packet-processing latency
feature-processing latency
FFT latency
ML inference latency
CPU usage
RAM usage

## ML

precision
recall
F1
fault recall
false-positive rate
false alarms/hour

## End-to-end

Measure timestamps around:

T0 sensor acquisition

T1 PC reception

T2 window completion

T3 feature completion

T4 ML inference completion

T5 state decision

T6 Arduino alarm command

T7 physical alarm activation where measurable

Report end-to-end detection latency.

Never fabricate benchmark numbers.

Create scripts to measure these quantities.

---

# 20. TESTING

Implement multiple test layers.

## Unit tests

Test:

* packet encoding/decoding
* CRC
* feature calculations
* windowing
* state transitions
* database operations

## Protocol tests

Inject:

* malformed packets
* truncated packets
* corrupted CRC
* sequence gaps
* unknown messages

## Integration tests

Test:

Arduino → Python

Python → Arduino

DAQ → processing

processing → ML

ML → alarm

## Failure tests

Physically or logically test:

* unplug USB
* reconnect USB
* restart Arduino
* stop Python
* corrupted serial input
* missing sensor
* invalid sensor readings

Record observed behaviour.

---

# 21. ENGINEERING DOCUMENTATION

Maintain professional documentation throughout development.

Create:

docs/
architecture/
hardware/
protocol/
experiments/
benchmarks/
decisions/
failures/

Document:

* problem statement
* requirements
* architecture
* BOM
* wiring
* schematic
* firmware architecture
* serial protocol
* sampling design
* signal processing
* feature engineering
* experimental methodology
* ML methodology
* model comparison
* benchmarks
* limitations
* failures encountered
* engineering decisions
* future improvements

Create Architecture Decision Records where a significant trade-off exists.

Examples:

ADR-001 — Why Arduino Uno

ADR-002 — Why SPI for vibration

ADR-003 — Why host-side ML

ADR-004 — Why Parquet + SQLite before PostgreSQL

ADR-005 — Why grouped dataset splitting

ADR-006 — Binary vs CSV serial protocol

---

# 22. PORTFOLIO OUTPUT

The final repository should support a professional case study.

The project should eventually demonstrate:

Electronics
→ Embedded Systems
→ Communication
→ Data Acquisition
→ Signal Processing
→ Data Engineering
→ Machine Learning
→ Real-Time Inference
→ Backend
→ Visualization
→ System Integration

Include:

* architecture diagrams
* wiring diagrams
* schematic
* photographs
* experiment photographs
* waveform plots
* FFT plots
* feature analysis
* confusion matrices
* model comparison
* benchmark tables
* failure analysis
* demonstration video

The README should emphasize measured engineering results rather than merely screenshots.

---

# 23. OPTIONAL EDGE-ML EXPERIMENT

Do NOT implement this until the host-side system is complete.

Investigate whether a small model could run on the Arduino Uno.

Candidates:

* threshold model
* logistic regression
* very small decision tree

Compare:

HOST ML vs EDGE ML

Measure:

* flash usage
* SRAM usage
* inference latency
* feature-computation requirements
* accuracy
* maintainability
* communication dependency
* power/resource constraints

Pay particular attention to the fact that running a tiny classifier may be easy while storing vibration windows and computing sophisticated features may be much harder on an ATmega328P with 2 KB SRAM.

Treat this as an engineering experiment, not a requirement.

---

# 24. TECHNOLOGY STACK

Prefer:

Embedded:
Arduino Uno
ATmega328P
C/C++
PlatformIO

Interfaces:
SPI
I²C
1-Wire
UART/USB

Python:
Python 3
PySerial
NumPy
SciPy
Pandas
PyArrow

ML:
scikit-learn
XGBoost only where justified

Storage:
Parquet
SQLite

Backend:
FastAPI

Dashboard:
Plotly Dash initially

Testing:
pytest
PlatformIO testing where practical

Version control:
Git

Do NOT introduce:

Kafka
RabbitMQ
Celery
Kubernetes
microservices
distributed databases

unless a later engineering requirement genuinely justifies them.

---

# 25. IMPLEMENTATION PHASES

Build the project incrementally.

## Phase 0 — Engineering foundation

Create:

* repository
* requirements
* architecture
* BOM
* initial documentation
* PlatformIO project
* Python environment

No ML.

## Phase 1 — Vibration sensor

Connect:

ADXL345 → Arduino

Verify:

* device detection
* XYZ measurements
* static orientation
* sensor configuration

Then:

Arduino → USB → Python

Display live acceleration.

This is the first complete vertical slice.

## Phase 2 — Deterministic DAQ

Implement controlled accelerometer sampling.

Measure:

* target sampling rate
* actual sampling rate
* jitter

Investigate limitations.

## Phase 3 — Serial transport

Implement V0 CSV.

Then implement binary protocol V1.

Add:

* sequence numbers
* timestamps
* CRC
* parser recovery
* packet-loss measurement

## Phase 4 — Complete sensing

Add:

INA219

DS18B20

LEDs

buzzer

Verify multi-rate sensor scheduling.

## Phase 5 — Python DAQ

Build robust:

* acquisition
* buffering
* reconnection
* logging
* storage

Run long-duration tests.

## Phase 6 — Signal processing

Implement:

* time-domain visualization
* filtering
* windowing
* FFT
* feature extraction

Compare NORMAL and deliberately altered physical conditions.

## Phase 7 — Dataset creation

Define experiment protocol.

Collect independent labelled runs.

Store metadata.

Validate dataset quality.

## Phase 8 — ML research

Perform EDA.

Build grouped train/validation/test partitions.

Train model ladder.

Compare models.

Select model.

## Phase 9 — Real-time intelligence

Integrate selected model with live DAQ.

Implement:

NORMAL
WARNING
FAULT

Add hysteresis/persistence.

## Phase 10 — Closed-loop alarm

Implement:

Python ML
→ serial command
→ Arduino
→ LED/buzzer

Measure response latency.

## Phase 11 — Storage/API/dashboard

Add:

SQLite/Parquet
FastAPI
Plotly Dash

Create live and historical monitoring.

## Phase 12 — Verification

Run:

* stress tests
* failure tests
* long-duration tests
* benchmark tests
* ML evaluation
* end-to-end latency tests

## Phase 13 — Portfolio

Produce:

* polished README
* engineering case study
* architecture diagrams
* schematic
* BOM
* benchmark tables
* ML results
* photographs
* demonstration video
* lessons learned

## Phase 14 — Optional Edge ML

Compare host ML against tiny Arduino-side inference.

---

# 26. HOW YOU SHOULD WORK WITH ME

Do NOT attempt to generate Phases 0–14 immediately.

We will work phase by phase.

For every phase:

1. State the engineering objective.
2. Explain the design.
3. Identify assumptions.
4. Identify hardware required.
5. Show wiring when relevant.
6. Define files/modules to create.
7. Implement the code.
8. Explain important sections of the code.
9. Provide build/run commands.
10. Provide a verification procedure.
11. Define expected behaviour without inventing measurements.
12. Identify likely failure modes.
13. Tell me what measurements/results I should record.
14. Update relevant documentation.
15. Define a clear acceptance criterion.

Do not proceed to the next phase until the current phase can be demonstrated working.

When debugging, diagnose the existing implementation before replacing large sections of code.

When proposing a dependency, explain why it is needed.

When making an engineering assumption, state it explicitly.

When multiple solutions exist, explain the trade-off and recommend one.

Keep the system realistic for one engineer working independently.

---

# FIRST TASK

Begin with **Phase 0 — Engineering Foundation** only.

Before writing firmware, establish the engineering specification.

Produce:

1. SentinelDAQ V1 requirements.
2. Functional requirements.
3. Non-functional requirements.
4. System architecture.
5. Hardware architecture.
6. Initial BOM.
7. Arduino Uno pin allocation.
8. Power architecture.
9. Sampling architecture.
10. Initial firmware architecture.
11. Initial Python architecture.
12. Repository structure.
13. Development environment requirements.
14. Initial risk register.
15. Engineering assumptions.
16. Phase 1 acceptance criteria.

Then create the initial repository/file structure and the minimum configuration files required to begin development.

Do not implement machine learning, FastAPI, dashboards or unnecessary later-stage components yet.

The immediate objective is to establish a disciplined engineering foundation from which we can begin **Phase 1: ADXL345 → Arduino Uno → USB → Python live vibration acquisition**.

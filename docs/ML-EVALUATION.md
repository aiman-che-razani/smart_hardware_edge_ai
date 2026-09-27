# ML evaluation: dataset eligibility, split plan, metrics, ledger

Owner: the `ml-evaluation` role. Written 2026-09-27 against the working tree at that date (line
numbers refer to it). Nothing here is a performance claim. **There is no physical result yet**; the
only numbers in this file that come from a model are labelled SYNTHETIC and validate code paths
and methodology, not the tank.

Items marked **USER DECIDES** carry a proposed value and a rationale. Nobody but the project
owner should change them after data collection starts.

## 1. Verdict

**Not eligible. No physical dataset exists, and the physical data cannot be trained on or evaluated.**

| Question | Answer (read-only analysis of a scratch copy of `data/physical` and `data/physical_check`) |
|---|---|
| Runs recorded | 9 (6 in `data/physical`, 3 in `data/physical_check`), 2026-09-19, 09-20 and 09-23; about 23.0k raw rows |
| Runs with status `COMPLETE` | 2, both in `physical_check`: a 20 s run (19 rows, **0 windows**) and a 1 h run (3598 rows, 105 windows). `data/physical` has **0** |
| Runs of any fault condition | **0**. All 9 are labelled `NORMAL` |
| Runs with a measured calibration | **0**. All 9 carry the placeholders (empty 1000 mm, full 50 mm, dry 200, wet 800), no `thermistor` entry, and an unfilled or empty `operator_metadata` |
| Runs `train.dataset()` would accept | **1**: the 1 h run `48b1ce36` (105 NORMAL windows). `dataset(data/physical)` raises `no completed feature runs` (`train.py:42-43`) |
| Would `train()` proceed? | No. On `physical_check` it passes the rate/window/calibration checks and stops at `need NORMAL plus a fault condition` (`train.py:83-85`). Even without that check `grouped_partitions` requires 3 runs per class (`train.py:26-27`) and there is 1 |
| Runs per class that qualify today | NORMAL 0 (1 by the code's own filter, 0 by the criteria in section 3), LOW_WATER 0, OVERFLOW 0, RAPID_DRAIN 0, SENSOR_MISMATCH 0, ENVIRONMENTAL_ANOMALY 0 |

Why the 1 h run is still excluded from a dataset: uncalibrated placeholders; 38.9% of samples invalid
(1367 of 3598 have no distance-valid flag); only 105 of a possible 238 windows were produced (56%
lost); no fault contrast; a single run and a single day.

The bring-up runs also show why the placeholder calibration cannot be used as a baseline: the median
`level_agreement_abs_mean` is 37 to 66 percentage points in every run except one (the demo score
saturates at 15), so the live demo
state machine reports WARNING or FAULT for a NORMAL-labelled rig (1 h run: 69 FAULT and 36 WARNING
of 105 windows, 0 NORMAL; 5 h run: 710 FAULT and 282 WARNING of 992). That is a calibration artefact,
not a false-alarm rate. The one exception, run `30284a5b`, reads exactly 0.0 because both level
channels are clipped to 0 (the ultrasonic was aimed away and the probe was dry).

### 1.1 Exclusion ledger for the bring-up runs (reasons, not silent drops)

| Run (prefix) | Dir | Date | Status | Rows | Windows | Reason excluded |
|---|---|---|---|---:|---:|---|
| 30284a5b | physical | 09-19 | INTERRUPTED | 189 | 11 | Not COMPLETE; placeholders; ultrasonic median 2212 mm (aimed away); probe dry (raw 8-11); NORMAL only |
| 1ba3ff02 | physical | 09-19 | INTERRUPTED | 485 | 26 | Not COMPLETE; placeholders; ultrasonic median 2212 mm; 7 invalid samples cost 5 windows |
| fe263795 | physical | 09-19 | INTERRUPTED | 540 | 28 | Not COMPLETE; placeholders; ultrasonic median 2207 mm; 10 invalid samples cost 7 windows |
| 0ef6e2a5 | physical | 09-19 | INTERRUPTED | 0 raw files | 36 | Not COMPLETE; raw Parquet missing (never flushed); no summary JSON; features cannot be re-derived |
| 1a285efb | physical | 09-20 | INTERRUPTED | 0 | 0 | Not COMPLETE; no samples received in 372 s |
| a8c0ebf2 | physical | 09-20 | INTERRUPTED | 18155 | 992 | Not COMPLETE (Ctrl-C ends a run as INTERRUPTED, `runner.py:199-200`); placeholders; probe at dry floor (raw 5-15, median 7) for the whole ~5 h |
| fb76dfcd | physical_check | 09-23 | INTERRUPTED | 0 | 0 | Not COMPLETE; no samples |
| e05e4450 | physical_check | 09-23 | COMPLETE | 19 | 0 | 20 s is shorter than one 30 s window; invisible to `dataset()` because of the inner join on `feature_window` (`train.py:38-40`) |
| 48b1ce36 | physical_check | 09-23 | COMPLETE | 3598 | 105 | Placeholders; 38.9% invalid samples; 56% of nominal windows lost; NORMAL only; no independent group |

Every row's summary is in `<dir>/<run_id>-summary.json` (git-ignored); the per-run figures above were
re-derived from `sentinel.sqlite` and the raw Parquet of a scratch copy. My replay of the window
rules (`processing/windows.py`, `pipeline.py:79-84`) over the raw rows reproduces the stored window
count exactly for all four runs that have raw files.

Small corrections to other docs that this analysis surfaced are in section 10.

## 2. What the tools actually do (verified 2026-09-27)

- Features (`processing/features.py:4-10`): 27 per window (6 channels x mean/slope/range/std, plus
  `level_agreement_abs_mean`, `level_agreement_abs_max`, `level_ultrasonic_min_slope_per_s`). The
  window is 30 s with 50% overlap by default (`windows.py:5-9`: size 30, step 15), configurable per
  run and recorded in the metadata and the model artifact.
- A window is produced only from 30 consecutive fully valid samples. **Any** invalid sample (a
  `None` in any of the 6 channels, `pipeline.py:79-84`), a sequence gap (`pipeline.py:75-78`) or a
  timing mismatch (`pipeline.py:88-96`) clears the window buffer and sets the state to UNKNOWN.
  Nothing is written for a discarded window; only a counter increments.
- `train.dataset()` (`train.py:36-46`) takes **every** `COMPLETE` run in the data directory whose
  `simulated` flag matches and that has at least one feature window; a `CYCLE` run anywhere in the
  set aborts training. It does not check the condition against the vocabulary, the calibration
  against the placeholders, the invalid rate, the gap count or the window count.
- `grouped_partitions` (`train.py:20-33`): stratified by class, per class `n = max(1, round(0.2 * runs))`
  runs go to test, `n` to validation and the rest to train; at least 3 runs per class; seed 42, not
  exposed on the CLI (`cli.py:80-82`). Run IDs are random UUIDs, so which runs land in test is
  effectively random.
- `train()` fits logistic regression (with `StandardScaler`), a depth-5 tree, a depth-8 random forest
  and an isolation forest on NORMAL training windows, plus a fixed threshold baseline; it selects among
  logistic/tree/forest by validation `fault_recall`, then `false_positive_rate`, then list position
  (`train.py:115-116`). The isolation forest and the threshold are reported, never selectable.
- `evaluate()` (`train.py:139-156`) recomputes the dataset hash (`145-147`), scores only the chosen
  model on the test windows and writes `test-report.json`; it refuses to overwrite that file
  (`141-143`).
- `metrics()` (`train.py:56-66`) is window-level only: per-class precision/recall/F1, a confusion
  matrix, `fault_recall` (any non-NORMAL prediction on a fault window), `false_positive_rate`,
  `missed_fault_windows`, ROC AUC and PR AUC. It records no run IDs, run counts, intervals or
  time-based quantities.
- Live scoring (`inference.py:36-47`, `state.py:5-37`): with no model the score is
  `min(1, level_agreement_abs_mean / 15)`. With a model it is `1 - P(NORMAL)`. The state machine
  (warning 0.5, fault 0.8, recovery 0.3) raises WARNING on a **single** window at or above 0.5,
  FAULT after 3 consecutive windows at or above 0.8, and returns to NORMAL only after 5 consecutive
  windows at or below 0.3. Start-up and every reset therefore need 30 valid samples plus 5 windows
  (about 90 s) before the state can be NORMAL.
- A model is refused if its feature schema, pipeline version, sampling rate, window configuration or
  calibration differ from the run's (`inference.py:31-34`, `pipeline.py:31-36`). Physical inference
  refuses a synthetic model (`inference.py:29-30`).

## 3. Eligibility criteria for a physical run

A run enters the training dataset only if **all** hold. Each is checked by the `ml-evaluation` role
on a read-only copy before `train`; today only C1, C2 and C10 are enforced by code.

| # | Criterion | Proposed value (USER DECIDES) | Rationale |
|---|---|---|---|
| C1 | Status | `COMPLETE`, reached by the full `--seconds` elapsing (never Ctrl-C) | `dataset()` filters on it; Ctrl-C yields INTERRUPTED (`runner.py:199-200`), which is why every bring-up run was excluded |
| C2 | Source | `simulated = 0`, `source = PHYSICAL`, no `CYCLE` run in the directory | `train.py:39,44` |
| C3 | Calibration measured | The four constants and the thermistor constants come from measurement per ADR-011 and are stored in `operator_metadata` with `calibration_measured: true`, the tape readings and the dry/wet medians | Percentages from placeholders are not meaningful (ADR-011). Code does not check this (risk R14) |
| C4 | One calibration per dataset | Identical constants for every run in the directory | `train.py:80-82` refuses mixed calibrations. Re-measure only when the tank or mounting changes, and then start a new dataset |
| C5 | Invalid-sample rate | at most **2%** of samples per run | Any invalid sample discards at least 30 samples of context. At an independent 2% rate a 300 s run yields about 62% of its nominal windows (section 5). The 5 h bring-up run had 1.6% (nearly all stale-DHT), the 1 h run 38.9% |
| C6 | Window yield | at least **60%** of the nominal windows `floor((D-30)/15)+1` | Guards against clustered dropouts that a rate alone hides |
| C7 | Sequence gaps / parser errors | 0 gaps in the labelled part of the run; parser errors reported in the summary | A gap clears the window and resets the state |
| C8 | Duration | at least **300 s** of recording (19 nominal windows), after a warm-up that is not recorded | 90 s gives only 5 windows, of which about 3 are non-overlapping; warm-up drift must not enter a labelled run |
| C9 | Label | `--condition` given explicitly, one of the six names in ADR-008, set by the operator from the procedure; one steady condition per run, or onset time recorded (section 6) | `--condition` defaults to `NORMAL` silently (`cli.py:14`) and accepts any string |
| C10 | Sampling rate / window config | 1 Hz, 30 s, 0.5 overlap, identical across the dataset | `train.py:74-79` |
| C11 | Metadata | tank, mounting id, session id, day, operator, fill state, ambient notes, warm-up minutes, run order, firmware build, condition onset time | Grouping and drift analysis need it. Not enforced |
| C12 | Sensor aim / plausibility | Ultrasonic aimed at open water (median distance within the taped empty/full range); probe wet at the intended depth; checked in a pilot capture before the dataset runs | The bring-up runs failed exactly this |
| C13 | Independence | A new `run_id`, a fresh fill/setup and a fresh `acquire` start for each run; the same condition is spread over at least 3 sessions/days | Back-to-back captures of an unchanged setup are near-duplicates |
| C14 | Exclusions | Every rejected run is listed with a reason in section 1.1 style, never deleted or hidden | Procedure step 5; note there is no exclusion mechanism in the tools (risk R12) |

## 4. The first physical dataset: concrete minimum

### 4.1 Conditions that can be produced safely (`docs/experiments/physical-procedure.md`, step 4)

| Condition | Producible as | Notes |
|---|---|---|
| NORMAL | Baseline fill at the normal mark | Yes |
| LOW_WATER | Lower the fill by hand to a low mark and hold | Yes |
| OVERFLOW | Raise the fill by hand to a high mark **without spilling** ("high-fill proxy") | The procedure allows raising the level; a real overflow near the electronics is not covered. USER DECIDES whether the proxy carries the OVERFLOW label |
| RAPID_DRAIN | Manual controlled lowering during the run | The procedure lists lowering by hand and "waiting for natural drain"; natural drain is far slower than the synthetic 1.2 %/s. The drain rate needs approval and onset time must be recorded |
| SENSOR_MISMATCH | Procedure says: offset one sensor's calibration in software | **Blocked by the tools**: the offset would travel in the calibration constants and `train()` refuses mixed calibrations (`train.py:80-82`, `runner.py:31-33`). A non-damaging physical proxy (a card held in the ultrasonic path, or a partly withdrawn probe) is not in the procedure and needs approval, or the code needs a separate offset field (R13) |
| ENVIRONMENTAL_ANOMALY | Brief covering/uncovering of the tank | Only a light/humidity proxy; the synthetic 40 C / 85% RH case cannot be produced safely. Defer |

Proposed first dataset **D1**: NORMAL, LOW_WATER and high-fill OVERFLOW proxy. RAPID_DRAIN,
SENSOR_MISMATCH and ENVIRONMENTAL_ANOMALY follow only after the decisions above.

### 4.2 Minimum counts (USER DECIDES)

| Level | Runs per class | Duration | Purpose |
|---|---|---|---|
| Code minimum | 3 (`train.py:26`) plus NORMAL | 90 s+ | Lets `train` run. Test = 1 run per class. **Pipeline rehearsal only; never reported as performance** |
| **Proposed D1** | **10 per class**, at least 3 sessions/days, at most 4 runs of a class per session | 300 s recording, after a 10 min warm-up | 2 test runs per class; still wide intervals (section 5.2) |
| Claim-worthy per class | 20+ | as D1 | Intervals of about 0.83 to 1.00 for an all-detected result (section 5.2) |

D1 recording time: 3 classes x 10 runs x 300 s = 2.5 h, plus setup between runs. Add a NORMAL soak
for the false-alarm rate (section 7): at least 3 sessions of at least 4 h (12 h total), each counting
as **one** independent run.

Windows per run (nominal, 1 Hz, 30 s / 0.5): 90 s gives 5, 180 s gives 11, 300 s gives 19, 600 s
gives 39. Windows are not independent samples; more windows never replace runs.

### 4.3 What `grouped_partitions` gives with R runs per class (D1 = 3 classes)

`n = max(1, round(0.2 R))`; Python rounds halves to even. Windows per test class assume 300 s runs
with 19 windows (5 windows for 90 s runs) and no invalid samples.

| R per class | test / validation / train runs per class | Test runs (3 classes) | Test windows per class (19 / 5 per run) | Independent runs behind each per-class metric and the NORMAL FPR |
|---|---|---|---|---|
| 3 | 1 / 1 / 1 | 3 | 19 / 5 | **1** |
| 5 | 1 / 1 / 3 | 3 | 19 / 5 | **1** (going from 3 to 5 adds no test evidence) |
| 10 | 2 / 2 / 6 | 6 | 38 / 10 | **2** |
| 20 | 4 / 4 / 12 | 12 | 76 / 20 | 4 |
| 25 | 5 / 5 / 15 | 15 | 95 / 25 | 5 |

The "detect any fault" recall pools the fault classes (2 classes x n runs in D1) but is a mix of
different conditions, so its effective sample is still small. Validation, which drives model
selection, has the same n per class.

## 5. Splits, intervals and exposure

### 5.1 Frozen-split plan

1. Record eligible runs **directly into a dedicated directory** (proposed `data/physical_d1`).
   `dataset()` takes every COMPLETE run in a directory and there is no tool to move or exclude one
   (R12), so pilots, rehearsals and rejects go to `data/physical_pilot`.
2. Group by session as well as run: no session may be entirely in test, and every class must appear
   in train from at least 2 sessions. The current tool groups by run only (R1); the role checks the
   assignment on a scratch copy before `train` and reports it. If it is unbalanced the fix is a code
   change (owner: ml/pipeline), not a different seed chosen after seeing the split.
3. Snapshot the directory (copy plus SHA-256 of `sentinel.sqlite`) **before** `train`, because `train`
   inserts a `model` row into the same database and any run added later invalidates the dataset hash
   (`train.py:133-135,145-147`).
4. Freeze the manifest: `splits.json`, the dataset hash and the model hash are recorded in the ledger
   (section 8) immediately after `train`. The test result is looked at once.

### 5.2 Intervals (two-sided 95% Clopper-Pearson, exact) for "k of n runs detected"

| n test runs | all detected | one missed |
|---:|---|---|
| 1 | 0.03 to 1.00 | (not applicable) |
| 2 | 0.16 to 1.00 | 0.01 to 0.99 |
| 3 | 0.29 to 1.00 | 0.09 to 0.99 |
| 4 | 0.40 to 1.00 | 0.19 to 0.99 |
| 6 | 0.54 to 1.00 | 0.36 to 1.00 |
| 10 | 0.69 to 1.00 | 0.56 to 1.00 |
| 20 | 0.83 to 1.00 | 0.75 to 1.00 |

Window-level intervals must be run-clustered (cluster bootstrap over runs) or, more simply, the run
counts above are quoted as the primary uncertainty. Quoting a binomial interval on 38 correlated
windows overstates precision.

### 5.3 Effective window yield versus invalid-sample rate (Monte Carlo, independent invalid samples)

Expected windows per run, mean of 400 simulations of the repo's window rules. Real dropouts are
clustered, so treat this as a rough guide (the 5 h bring-up run at 1.6% invalid kept 82% of its
windows).

| Run length | nominal | 0.5% | 1% | 2% | 5% | 10% |
|---|---:|---:|---:|---:|---:|---:|
| 90 s | 5 | 4.3 | 3.7 | 2.8 | 1.4 | 0.4 |
| 180 s | 11 | 9.6 | 8.6 | 6.6 | 3.1 | 0.9 |
| 300 s | 19 | 16.7 | 14.7 | 11.7 | 5.4 | 1.5 |
| 600 s | 39 | 34.4 | 30.5 | 24.2 | 11.6 | 3.2 |

## 6. Physical data-collection plan

Coordinate hardware steps with `hardware-bringup`; no wiring changes while powered.

1. **Calibrate first** (ADR-011): dry/wet water-probe medians (60 s each, 3 repeats), tape-measured
   empty/full distance with the ultrasonic aimed straight down at open water, thermistor part and DHT
   variant identified. Store them in the metadata file; pass the same numbers to every run.
2. **Pilot capture** into `data/physical_pilot`: 5 min at the normal fill. Pass only if C5, C6, C7 and
   C12 hold. Fix aim or wiring, not the thresholds.
3. **Session design**: at least 3 sessions on different days; per session up to 4 runs of each class;
   randomise condition order within the safety limits (write the order to the run metadata before
   starting, not after); note ambient temperature/humidity and warm-up time. Re-set the fill level
   between runs of the same class.
4. **Run metadata** (free-form keys are accepted in `operator_metadata`, `runner.py:28`): `session_id`,
   `day`, `mounting_id`, `tank`, `operator`, `fill_start_pct_tape`, `warmup_min`, `run_order`,
   `condition_onset_s` (seconds after start when the condition began, 0 for steady conditions),
   `calibration_measured`, `firmware_build`, `ambient_temp_c_note`, `notes`.
5. **Steady conditions** for LOW_WATER and OVERFLOW proxy: hold the level for the whole run. For any
   transient condition (RAPID_DRAIN) record `condition_onset_s`; windows that overlap the transition
   are reported as TRANSITION, counted, and excluded from window metrics only in a listed way.
6. **After each run**: inspect the summary JSON (gaps, invalid, parser errors, windows). Log a
   pass/fail row against C1 to C14. Do not discard failed runs silently.
7. **Freeze** per section 5.1 and hand the directory to the role for the read-only pre-train check.

## 7. Metric definitions

Every reported figure carries its counts (windows and independent runs) and its interval.

**Window level** (on windows that exist; see "no-decision" below):
- Fault recall = fault windows predicted non-NORMAL / fault windows. Per-class recall from the
  confusion matrix, which is always shown.
- NORMAL false-positive rate = NORMAL windows predicted non-NORMAL / NORMAL windows.
- Missed-fault windows (count), confusion matrix (counts). ROC AUC and PR AUC only alongside those,
  and PR AUC is quoted with its prevalence baseline (a balanced test set with 5 fault classes of 6
  has a no-skill precision of 0.83).
- Accuracy is not reported as a headline.

**No-decision windows**: for every run report nominal windows, produced windows, and the fraction of
run time in UNKNOWN. In a fault run, time with no window is not detection. Report a "detected or
flagged UNKNOWN" figure separately so a fault that blinds a sensor is visible.

**Run level** (the primary evidence, because runs are the independent units):
- A fault run is *detected* if the replayed state machine reaches FAULT after `condition_onset_s`;
  *warned* if WARNING or FAULT. A NORMAL run is a *false-alarm run* if it enters WARNING or FAULT.
- Reported as k of n with the Clopper-Pearson interval, per class, plus per-run values so variation
  between runs is visible.

**Operational**:
- False alarms per hour of NORMAL operation = FAULT (and, separately, WARNING) entries in the
  replayed state machine / NORMAL hours. Replay: feed the stored `feature_window` rows of each run in
  timestamp order through `Inference.score` and `StateMachine.update`, calling `update(None)` where the
  gap between consecutive windows exceeds the step (the pipeline reset the buffer). Hours =
  sum over runs of (windows x 15 s) / 3600. Report the alarm count with an exact Poisson interval.
  With zero false alarms the 95% upper bound is about `3 / hours`: 12 h of NORMAL gives 0.25 per
  hour, and a "no more than 1 per day" claim needs about 72 h. Alarms are assumed roughly
  independent, which must be stated.
- Time to detect = seconds from `condition_onset_s` to the first FAULT. Its floor with 30 s windows
  and persistence 3 is about 60 s (window fill 30 s plus two more windows at 15 s), plus up to 15 s of
  window phase; the median and worst case are reported over runs.
- Availability = fraction of run time not in UNKNOWN.

**Baselines** (declared before the test is opened; a model must beat them on the same test runs to be
selected, rule 4):
- Naive: always NORMAL (recall 0) and always FAULT (recall 1, FPR 1).
- The repo's threshold rule, `level_agreement_abs_mean >= 12` (score 0.8 x 15). By construction it can
  only detect SENSOR_MISMATCH.
- A fixed per-class rule on the same features (low-level band, high-level band, slope, ambient
  range), thresholds written down before looking at data. Proposed; USER DECIDES the rules.

The score is an engineering index, not a calibrated probability. No probability or calibration
language is used without a calibration analysis on held-out runs.

## 8. Evaluation ledger

### 8.1 Physical

| Date | Dataset dir and hash | Split manifest | Model (kind, hash) | Runs per class (train/val/test) | Test result | Notes |
|---|---|---|---|---|---|---|
| (none) | | | | | | No eligible physical dataset exists. No physical model has been trained or evaluated. |

### 8.2 Synthetic (SYNTHETIC ONLY; not tank performance)

| Date | What | Source file | Numbers |
|---|---|---|---|
| 2026-09-18 | Repo synthetic ML workflow, 18 runs (3 per class), 90 s, split 6/6/6 | `docs/benchmarks/synthetic-model-validation.json`, `docs/benchmarks/synthetic-model-test.json` | Validation: tree selected (recall 1.0, FPR 0.0 on 5 NORMAL windows); test (30 windows, 1 run per class): fault recall 0.96 (24/25 fault windows), FPR 0.20 (1 of 5 NORMAL windows, one run), accuracy 0.80, ROC AUC 0.88, PR AUC 0.955 against a no-skill 0.83. LOW_WATER and RAPID_DRAIN are confused with each other; the test set is far too small for any interval |
| 2026-09-27 | Leakage and variance experiments (section 9) | scratch only, not in the repo | see section 9 |
| 2026-09-15 | Pre-pivot motor/vibration workflow | `docs/benchmarks/*-pre-pivot.json`, `data/models/synthetic-v1` | Historical; the artifact lacks a calibration and is refused by the current code |

## 9. Synthetic sanity experiments (SYNTHETIC ONLY)

Purpose: measure how much the repo's evaluation choices can mislead, and how noisy the numbers are at
3, 5 and 10 runs per class. **None of these numbers describe the tank or any physical performance.**

Method. 120 synthetic runs (20 per class x 6 classes, 90 s, 5 windows each, 600 windows) were generated
into a scratch directory with `sentinel dataset --runs 20 --seconds 90`. Models were fitted in-process
with the repo's own `grouped_partitions`, `dataset`, `metrics` conventions and the same three
candidates and selection rule; `train()` and `evaluate()` were not called. 100 repetitions per cell,
varying the split seed and the run subset; the model seed stays 42.

The generator gives every run of a class the same deterministic signal plus fresh noise, so runs have
no identity of their own. To mimic the persistent per-run effects that real mounting, day and
calibration differences add, a second family adds a per-run offset to the channel-mean features
(level pair 6 pts each, temperature 2 C, humidity 6%, thermistor 3 C, light 8%, all times a factor K
of 1, 2 or 3; the agreement features shift by the level offset difference). **These offsets are an
arbitrary illustration**, not measured, and are labelled `effects_xK` below.

### 9.1 Leakage: run-grouped split versus random window split (about 120 test windows each)

Selected model (validation recall, then FPR, then simplicity), mean over 100 repetitions:

| Data | Accuracy, run-grouped | Accuracy, random-window | Optimism | FPR run-grouped / random | Forest accuracy run-grouped / random |
|---|---|---|---|---|---|
| plain generator | 0.926 | 0.928 | -0.002 | 0.000 / 0.000 | 0.998 / 0.997 |
| effects_x1 | 0.912 | 0.934 | +0.022 | 0.000 / 0.000 | 0.912 / 0.943 |
| effects_x2 | 0.880 | 0.927 | +0.047 | 0.037 / 0.013 | 0.891 / 0.944 |
| effects_x3 | 0.844 | 0.917 | +0.073 | 0.117 / 0.052 | 0.859 / 0.934 |

Reading: on the unmodified generator the leakage is **invisible**, because runs have no persistent
identity, so this generator cannot be used to demonstrate that the grouped split matters. Once runs
carry any persistent offset, a random window split reports accuracy 2 to 7 points higher and an FPR
2 to 3 times lower than the run-grouped split on the same data, and the gap grows with the size of the
run effect. Real runs from one mounting on one day will have such effects.

Side observation from the plain generator: the selection rule picks logistic regression in 75 to 100
of 100 repetitions (ties on recall and FPR fall through to "simplicity") although the tree and forest
score 0.996 to 0.998 accuracy against logistic's 0.926, because `fault_recall` does not see
misclassification between fault types (R2, R15).

### 9.2 Variance: test metrics versus runs per class (selected model, repo split)

Run-level columns use the repo `StateMachine` over each 5-window test run (so they are very coarse).
`FA runs` = fraction of NORMAL test runs that entered WARNING or FAULT.

| Data | R | Test runs/class | Test windows | Fault recall mean (sd, min) | FPR mean (sd, max) | Fault runs reaching FAULT, mean (sd) | FA runs mean (sd) |
|---|---:|---:|---:|---|---|---|---|
| plain | 3 | 1 | 30 | 0.997 (0.014, 0.92) | 0.040 (0.102, 0.60) | 0.90 (0.11) | 0.58 (0.50) |
| plain | 5 | 1 | 30 | 1.000 (0.000, 1.00) | 0.002 (0.020, 0.20) | 1.00 (0.03) | 0.02 (0.14) |
| plain | 10 | 2 | 60 | 1.000 (0.000, 1.00) | 0.000 (0.000, 0.00) | 1.00 (0.00) | 0.00 (0.00) |
| effects_x1 | 3 | 1 | 30 | 0.952 (0.078, 0.68) | 0.360 (0.400, 1.00) | 0.81 (0.19) | 0.82 (0.39) |
| effects_x1 | 5 | 1 | 30 | 0.996 (0.019, 0.84) | 0.038 (0.138, 1.00) | 0.92 (0.11) | 0.25 (0.44) |
| effects_x1 | 10 | 2 | 60 | 0.998 (0.011, 0.90) | 0.005 (0.022, 0.10) | 0.98 (0.05) | 0.03 (0.11) |
| effects_x2 | 3 | 1 | 30 | 0.893 (0.124, 0.56) | 0.536 (0.470, 1.00) | 0.78 (0.23) | 0.89 (0.31) |
| effects_x2 | 5 | 1 | 30 | 0.969 (0.063, 0.68) | 0.166 (0.301, 1.00) | 0.89 (0.13) | 0.60 (0.49) |
| effects_x2 | 10 | 2 | 60 | 0.986 (0.034, 0.80) | 0.074 (0.145, 0.60) | 0.94 (0.09) | 0.23 (0.31) |
| effects_x3 | 3 | 1 | 30 | 0.884 (0.138, 0.40) | 0.638 (0.452, 1.00) | 0.78 (0.22) | 0.85 (0.36) |
| effects_x3 | 5 | 1 | 30 | 0.948 (0.081, 0.60) | 0.286 (0.365, 1.00) | 0.86 (0.15) | 0.69 (0.47) |
| effects_x3 | 10 | 2 | 60 | 0.969 (0.046, 0.76) | 0.141 (0.211, 1.00) | 0.90 (0.09) | 0.51 (0.40) |

Reading: with 1 test run per class the NORMAL FPR is measured on 5 windows of one run, so it takes
values in {0, 0.2, ..., 1.0}; the same code and data give anything from 0 to 1 depending only on which
runs land in test (plain R=3: FPR 0 to 0.60; effects_x1 R=3: 0 to 1.00). Going from R=3 to R=5 leaves
the test set unchanged (1 run per class) and only improves training. Even at R=10 (2 test runs per
class) the spread stays large once run effects exist. These are the reasons for the run-count
proposal in section 4.2.

Raw output: scratchpad `ml_eval/exp_100.txt` and `exp_100.json` (not in the repo); the scripts are
`exp.py` and `tables.py` in the same scratch directory.

## 10. Documentation discrepancies found (not edited here)

- `docs/decisions/README.md`, ADR-011 row: says the constants are "not stored in model artifact". The
  code stores them (`train.py:122`) and the ADR body says so.
- `docs/decisions/README.md`, ADR-005 row: only says "group splits by run_id". The
  session/mounting/day rule comes from `docs/experiments/physical-procedure.md` step 7, not ADR-005.
  ADR-001 to ADR-006 have no separate files.
- `docs/experiments/README.md`: says `physical_check` holds "a 20 s run and a 1 h run"; it holds three
  runs (an INTERRUPTED zero-sample run `fb76dfcd` as well). The runs are on three days
  (2026-09-19, 09-20, 09-23), not one; the machine label `tank-1` is the `--machine` default
  (`cli.py:24`), so it is not evidence of one physical tank.

## 11. Methodology risk register

Severity: H = would produce a misleading physical result, M = weakens the result, L = minor.
Owner is the role that should make the change; `ml-evaluation` does not edit source.

| ID | Sev | Flaw | Evidence | Minimal fix |
|---|---|---|---|---|
| R1 | H | Split groups by run only; no session, mounting or day grouping; seed 42 not exposed; assignment is effectively random via UUID run IDs. Runs from one session can land on both sides | `train.py:20-33`, `train.py:83,86`, `cli.py:80-82` | Take a `group` key (`operator_metadata.session_id`) into `grouped_partitions`, hold whole sessions out per class where possible, print the manifest; keep run-level as the fallback |
| R2 | H | Selection is lexicographic on any-fault recall then FPR: (a) ignores type confusion (synthetic: logistic at 0.926 accuracy beats a 0.996 tree, section 9.1); (b) an always-FAULT model (recall 1.0) beats any model with one missed window; (c) with 1 to 2 NORMAL validation runs FPR has 5 to 10 windows of resolution, so ties resolve by "simplicity"; (d) five candidates compared on one tiny validation set | `train.py:115-116`, `train.py:58` | Prespecify the model family and decision rule before data, or select by run-level worst-class recall subject to an FPR ceiling, using grouped cross-validation over train and validation runs; report validation with its counts |
| R3 | M | Isolation-forest score `sigmoid(20 x decision_function)` with a 0.5 cut is arbitrary: a risk of 0.5 means `decision_function = 0`, which is sklearn's default cut for `contamination="auto"`, and the state machine's 0.8 corresponds to a decision value of -0.069. Assumes the NORMAL training runs are pure and stationary (warm-up drift, contamination unknown). It is never selectable, so `inference.py:43-44` is dead, and `evaluate` would fail for it (no `classes_`). Its 0.167 "accuracy" is an artefact of the `ANOMALY` label | `train.py:102-103`, `train.py:115`, `train.py:152`, `inference.py:43-44` | If kept: choose the cut as a quantile of validation-NORMAL decision values (target FPR or false alarms per hour), report it as an anomaly detector with that operating point, or delete the branch |
| R4 | M | The threshold baseline is a fixed 12-point rule (score 0.8 x 15), scored on validation only, absent from `evaluate`; it can only detect SENSOR_MISMATCH (recall 0.20 = 1 of 5 fault classes), so it is a strawman. No naive baseline. Design rule 4 ("must beat the threshold") is not enforced | `train.py:112-113`, `train.py:152` | Compute all declared baselines in `evaluate` on the same test windows, add a per-class rule baseline (section 7), and make selection conditional on beating them |
| R5 | M | No class weighting; window counts follow run length, so a 5 h run (992 windows) outweighs a 5 min run 50 to 1 in fitting and in pooled metrics | `train.py:90-92`, `train.py:56-66` | Equal-duration runs (C8), cap windows per run or weight by 1/windows-in-run, report per-class and per-run values |
| R6 | H | Metrics are window-level only: no run-level results, no run counts, no per-run variation, no intervals, no time-based quantities. `arrays()` drops the run ID | `train.py:49-53`, `train.py:56-66`, `train.py:152` | Add a per-run table, k/n with exact intervals, and run-clustered bootstrap for window metrics to `evaluate` (section 7) |
| R7 | H | False alarms per hour are never computed; the evaluation ignores the state machine's persistence (3) and recovery (5) and the WARNING single-window trigger, so window FPR says nothing about the alarm rate an operator sees | `train.py:56-66` vs `state.py:22-37`, `pipeline.py:103` | Replay stored features through `Inference.score` and `StateMachine.update` per run with resets at window gaps (section 7) |
| R8 | H | No confidence intervals anywhere. The synthetic test report's FPR of 0.20 is 1 window of 5 from a single run | `docs/benchmarks/synthetic-model-test.json`, `train.py:56-66` | Section 5.2 |
| R9 | ok | Scaling and leakage across runs: `StandardScaler` sits inside the pipeline and fits on train windows only (isolation forest: NORMAL train only); no hyperparameter tuning uses test; the split is by run. No leakage found in the fit path | `train.py:90,93,98-99` | None. Still no per-run/day normalisation, so calibration must be identical across the dataset (C4) |
| R10 | H | Survivorship: any invalid sample discards the window buffer and nothing is stored for the lost windows, so the dataset and every metric are conditional on healthy sensors. The 1 h bring-up run lost 133 of 238 nominal windows (56%) at 38.9% invalid samples; each invalid sample also forces about 90 s of UNKNOWN. A fault that blinds a sensor (echo too close, out of range, foam) leaves few or no windows and looks better than it is | `pipeline.py:79-84`, `state.py:35-36`, `windows.py:14-17` | Report nominal versus produced windows and UNKNOWN time per run and class; count fault-run time without a decision as not detected; consider per-channel validity so one stale DHT read does not discard the level features (pipeline owner) |
| R11 | H | "Evaluate once" is per model directory, not per dataset: `train` into a new directory (same seed, same runs, so the same test runs) followed by `evaluate` gives a second look at the test set | `train.py:71-72`, `train.py:141-143` | Write an evaluation record keyed by `dataset_sha256` into the data directory at `evaluate` and refuse any second one for that hash |
| R12 | M | The dataset hash covers every COMPLETE run in the directory, so any later run blocks `evaluate`; there is no way to exclude a run (only 0-window runs vanish silently through the inner join); reasons for exclusion cannot be recorded | `train.py:38-40`, `train.py:145-147` | A `sentinel exclude --run-id --reason` that sets a non-COMPLETE status and appends the reason to the metadata; until then use separate directories (section 5.1) |
| R13 | H | Labels: `--condition` defaults to NORMAL silently and takes any string; one label per run with no fault onset, so transition windows carry the wrong label; SENSOR_MISMATCH by software offset travels in the calibration constants and `train` refuses mixed calibrations, so those runs cannot be trained together with the others | `cli.py:14`, `runner.py:31-33`, `train.py:80-82`, `database.py:77-87` | Validate `--condition` against ADR-008 with no default for `acquire`; store `condition_onset_s`; keep a sensor-offset field separate from the calibration, or approve a physical proxy |
| R14 | H | The calibration gate is not enforced: `from_metadata` accepts the placeholders, so an uncalibrated run passes `dataset()` | `calibration.py:24-31`, `train.py:80-82` | Require `operator_metadata.calibration_measured` (or a `--calibrated` flag recorded in the run) in `dataset()` |
| R15 | M | "Detected" means any non-NORMAL prediction, so a LOW_WATER run classified as OVERFLOW counts as detected; per-class recall exists only inside `classification_report` and is not used for selection | `train.py:58-62` | Report detection and correct-type recall separately at run level |
| R16 | M | State thresholds 0.5/0.8/0.3 act on `1 - P(NORMAL)` from models trained on artificially balanced classes; forest vote fractions and logistic probabilities are not calibrated and the deployed NORMAL prior is close to 1. PR AUC on a set that is 83% fault windows is prevalence-dependent | `state.py:6-11`, `train.py:66`, `inference.py:45-47` | Choose the operating point on validation-NORMAL windows for a target false-alarm rate; quote PR AUC only with its baseline |
| R17 | L | Level channels are clipped to 0-100, so out-of-range levels saturate and the agreement feature goes blind (run `30284a5b` reads 0.0) | `pipeline.py:12-15,62-64` | Keep the unclipped value as a validity flag or feature |
| R18 | M | Warm-up, run order and ambient drift are not recorded or randomised by the tooling; one tank and one mounting limit generalisation | procedure step 6, `run-template.json` | Metadata keys in section 6; claims limited to the recorded setup (rule 8) |

## 12. How to run train and evaluate once (for the user, when eligible)

Do not run any of this until section 3 has been checked on the whole dataset, the split preview has
been reviewed, the ledger row is prepared and a directory snapshot exists. These commands write to the
data directory and to `data/models`; that is why the `ml-evaluation` role never runs them.

Pre-flight (all read-only, done by the role on a scratch copy):
1. Every run in `data/physical_d1` meets C1 to C14; the exclusion table is written; no `CYCLE` or
   simulated run is present.
2. Calibration constants identical across runs and equal to the measured values.
3. Split preview: `grouped_partitions(labels, 42)` classes, session spread and windows per split
   reviewed once, before any model is trained.
4. Snapshot: `Copy-Item -Recurse data\physical_d1 data\physical_d1_snapshot` and record the SHA-256 of
   `data\physical_d1\sentinel.sqlite`.

Record a run (repeat per run; the calibration flags are the measured numbers):

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/physical_d1 acquire --port COMx --seconds 300 `
  --condition LOW_WATER --machine tank-1 --metadata-json runs\S2-run07.json `
  --distance-empty-mm <tape> --distance-full-mm <tape> --water-dry-raw <median> --water-wet-raw <median> `
  --notes "session S2, run 7, low mark held"
```

Train (once per dataset; the output directory must not exist; the default is PHYSICAL, do **not** pass
`--simulated`):

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/physical_d1 train --output data/models/physical-d1-v1
```

Read `data/models/physical-d1-v1/report.json` (validation only) and `splits.json`. Record in the
ledger: date, dataset directory and hash, `splits.json`, model kind and `model_sha256`, runs per class
in each split. Do not change the model, features, thresholds or split after this point. If anything
must change, start a new dataset version and a new ledger row; the current test runs are then spent.

Evaluate (exactly once, and only if the baselines and the analysis plan in section 7 are already
written down):

```powershell
.\.venv\Scripts\python.exe -m sentinel --data data/physical_d1 evaluate --model-dir data/models/physical-d1-v1
```

`evaluate` writes `test-report.json` and refuses a second run in that directory (but see R11: a new
directory would not be refused, so do not do that). Then hand `test-report.json` to the role to add
the run-level, false-alarm and baseline analysis of section 7 on a scratch copy, enter it in section
8.1, and pass the wording to the `evidence` agent. Until the run-level and interval parts exist in the
tooling (R6, R7), the window-level report alone must not be quoted as a result.

Physical inference (later): `acquire --model data\models\physical-d1-v1\model.joblib` with the same
calibration constants, sampling rate and window settings; a synthetic model is refused.

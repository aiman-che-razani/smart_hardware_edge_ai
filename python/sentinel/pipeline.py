"""Single processing owner; acquisition uses a bounded queue in runner.py."""
import time
import numpy as np
from sentinel.acquisition.protocol import Continuity, DISTANCE_VALID, AMBIENT_VALID
from sentinel.processing.features import extract, CHANNELS
from sentinel.processing.windows import Windows
from sentinel.state import StateMachine
from sentinel.ml.inference import Inference


def _clip_pct(value):
    return max(0.0, min(100.0, value))


class Pipeline:
    def __init__(self, store, fs=1, model=None, simulated=False, overlap=0.5, seconds=30,
                 state_config=None,
                 distance_empty_mm=1000, distance_full_mm=50,
                 water_dry_raw=200, water_wet_raw=800):
        self.store, self.fs = store, fs
        self.windows = Windows(round(fs*seconds), overlap)
        self.continuity = Continuity()
        self.state = StateMachine(**(state_config or {}))
        self.inference = Inference(model, allow_simulated=simulated)
        if self.inference.artifact and self.inference.artifact["fs"] != fs:
            raise ValueError("model sampling rate mismatch")
        if self.inference.artifact and self.inference.artifact["window"] != {"seconds":seconds,"overlap":overlap}:
            raise ValueError("model window configuration mismatch")
        # Tank/sensor calibration. All placeholders pending the real hardware's
        # exact geometry/part specs; see docs/hardware/design.md.
        self.distance_empty_mm, self.distance_full_mm = distance_empty_mm, distance_full_mm
        self.water_dry_raw, self.water_wet_raw = water_dry_raw, water_wet_raw
        self.count = self.window_count = self.invalid = 0
        self.last_window = None
        self.last_record = None
        self.latencies = []

    def disconnect(self):
        self.windows.clear()
        self.continuity.previous = None
        self.state.update(None)
        self.store.transition(time.time(), "UNKNOWN")

    def _thermistor_temp_c(self, raw):
        # Placeholder NTC beta approximation (10k series, 10k @25C, beta=3950) —
        # replace the constants once the fitted thermistor's datasheet is known.
        if raw <= 0 or raw >= 1023:
            return None
        resistance = 10000.0 * raw / (1023 - raw)
        inv_t = 1/298.15 + (1/3950.0) * np.log(resistance/10000.0)
        return float(1/inv_t - 273.15)

    def accept(self, sample, host_ns):
        accepted, gap = self.continuity.accept(sample)
        if not accepted:
            return None
        distance_ok = bool(sample.flags & DISTANCE_VALID)
        ambient_ok = bool(sample.flags & AMBIENT_VALID) and sample.ambient_age_ms <= 4000
        level_ultrasonic_pct = _clip_pct(100*(self.distance_empty_mm-sample.distance_mm) /
                                          (self.distance_empty_mm-self.distance_full_mm)) if distance_ok and sample.distance_age_ms <= 1000 else None
        level_water_pct = _clip_pct(100*(sample.water_level_raw-self.water_dry_raw) /
                                     (self.water_wet_raw-self.water_dry_raw))
        record = dict(sample.__dict__, host_timestamp_ns=host_ns,
                      level_ultrasonic_pct=level_ultrasonic_pct, level_water_pct=level_water_pct,
                      ambient_temp_c=sample.ambient_temp_c_ds/10 if ambient_ok else None,
                      ambient_humidity_pct=sample.ambient_humidity_ds/10 if ambient_ok else None,
                      thermistor_temp_c=self._thermistor_temp_c(sample.thermistor_raw),
                      light_pct=_clip_pct(sample.light_raw/1023*100))
        self.store.raw(record)
        self.last_record = record
        self.count += 1
        if gap:
            self.windows.clear()
            self.state.update(None)
            self.store.transition(host_ns/1e9, "UNKNOWN")
        if not distance_ok or level_ultrasonic_pct is None or any(record[c] is None for c in CHANNELS):
            self.invalid += 1
            self.windows.clear()
            self.state.update(None)
            self.store.transition(host_ns/1e9, "UNKNOWN")
            return None
        window = self.windows.add(record)
        if window is None:
            return None
        # Reject windows whose device readout timing is inconsistent with the declared rate.
        duration = (window[-1]["timestamp_ms"]-window[0]["timestamp_ms"]) & 0xFFFFFFFF
        expected = (len(window)-1)*1000/self.fs
        if not 0.9*expected <= duration <= 1.1*expected:
            self.windows.clear()
            self.state.update(None)
            self.invalid += 1
            self.store.transition(host_ns/1e9, "UNKNOWN")
            return None
        start = time.perf_counter()
        features = extract(window, self.fs)
        feature_ms = (time.perf_counter()-start)*1000
        inference_start = time.perf_counter()
        score = self.inference.score(features)
        latency = (time.perf_counter()-inference_start)*1000
        state = self.state.update(score)
        self.store.window(host_ns/1e9, features, self.inference.version, state, score, latency)
        self.window_count += 1
        self.last_window = window
        self.latencies.append((feature_ms, latency))
        if len(self.latencies) > 10000:
            del self.latencies[:5000]
        return state

    def summary(self):
        return {"samples": self.count, "windows": self.window_count, "state": self.state.state,
                "sequence_gaps": self.continuity.gaps, "resets": self.continuity.resets,
                "duplicates": self.continuity.duplicates, "out_of_order": self.continuity.out_of_order,
                "invalid_windows_or_samples": self.invalid,
                "feature_ms_p50": float(np.median([x[0] for x in self.latencies])) if self.latencies else None,
                "inference_ms_p50": float(np.median([x[1] for x in self.latencies])) if self.latencies else None,
                "last_record": self.last_record}

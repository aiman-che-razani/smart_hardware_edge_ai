"""Single processing owner; acquisition uses a bounded queue in runner.py."""
import time
import numpy as np
from sentinel.acquisition.protocol import Continuity, ACC_VALID, CURRENT_VALID, TEMP_VALID, OVERRUN
from sentinel.processing.features import extract
from sentinel.processing.windows import Windows
from sentinel.state import StateMachine
from sentinel.ml.inference import Inference


class Pipeline:
    def __init__(self, store, fs=800, model=None, simulated=False, overlap=0.5, seconds=1.0, state_config=None):
        self.store, self.fs = store, fs
        self.windows = Windows(round(fs*seconds), overlap)
        self.continuity = Continuity()
        self.state = StateMachine(**(state_config or {}))
        self.inference = Inference(model, allow_simulated=simulated)
        if self.inference.artifact and self.inference.artifact["fs"] != fs:
            raise ValueError("model sampling rate mismatch")
        if self.inference.artifact and self.inference.artifact["window"] != {"seconds":seconds,"overlap":overlap}:
            raise ValueError("model window configuration mismatch")
        self.scale = 0.0039
        self.shunt_ohms = 0.1
        self.count = self.window_count = self.invalid = 0
        self.last_window = None
        self.latencies = []

    def disconnect(self):
        self.windows.clear()
        self.continuity.previous = None
        self.state.update(None)
        self.store.transition(time.time(), "UNKNOWN")

    def accept(self, sample, host_ns):
        accepted, gap = self.continuity.accept(sample)
        if not accepted:
            return None
        record = dict(sample.__dict__, host_timestamp_ns=host_ns)
        record.update(ax_g=sample.ax*self.scale, ay_g=sample.ay*self.scale, az_g=sample.az*self.scale,
                      current_a=sample.shunt_raw*1e-5/self.shunt_ohms if sample.flags & CURRENT_VALID and sample.current_age_ms <= 200 else None,
                      temperature_c=sample.temp_raw/16 if sample.flags & TEMP_VALID and sample.temp_age_ms <= 2000 else None)
        self.store.raw(record)
        self.count += 1
        if gap or sample.flags & OVERRUN:
            self.windows.clear()
            self.state.update(None)
            self.store.transition(host_ns/1e9, "UNKNOWN")
        if not sample.flags & ACC_VALID:
            self.invalid += 1
            self.windows.clear()
            self.state.update(None)
            self.store.transition(host_ns/1e9, "UNKNOWN")
            return None
        window = self.windows.add(record)
        if window is None:
            return None
        # Reject windows whose device readout timing is inconsistent with the declared rate.
        duration = (window[-1]["timestamp_us"]-window[0]["timestamp_us"]) & 0xFFFFFFFF
        expected = (len(window)-1)*1e6/self.fs
        if not 0.95*expected <= duration <= 1.05*expected:
            self.windows.clear()
            self.state.update(None)
            self.invalid += 1
            self.store.transition(host_ns/1e9, "UNKNOWN")
            return None
        start = time.perf_counter()
        features = extract([[r["ax_g"], r["ay_g"], r["az_g"]] for r in window], self.fs)
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
                "inference_ms_p50": float(np.median([x[1] for x in self.latencies])) if self.latencies else None}

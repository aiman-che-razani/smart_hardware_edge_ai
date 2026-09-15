import numpy as np
import joblib
from sentinel.processing.features import FEATURE_NAMES


class Inference:
    def __init__(self, path=None, allow_simulated=False):
        self.artifact = joblib.load(path) if path else None  # Only load trusted local artifacts.
        self.version = self.artifact["version"] if self.artifact else "threshold-demo-v1"
        if self.artifact and self.artifact["simulated"] and not allow_simulated:
            raise ValueError("synthetic model is forbidden for physical inference")
        if self.artifact and self.artifact["features"] != FEATURE_NAMES:
            raise ValueError("model feature schema differs from pipeline")

    def score(self, features):
        if self.artifact is None:
            # Engineering demo score, not a calibrated fault probability.
            return min(1.0, max(features[f"{a}_rms"] for a in "xyz") / 0.25)
        x = [[features[name] for name in FEATURE_NAMES]]
        model = self.artifact["model"]
        if self.artifact["kind"] == "isolation":
            return float(1 / (1 + np.exp(np.clip(model.decision_function(x)[0]*20, -50, 50))))
        probabilities = model.predict_proba(x)[0]
        normal = list(model.classes_).index("NORMAL")
        return float(1-probabilities[normal])

import hashlib
import io
from pathlib import Path
import numpy as np
import joblib
from sentinel.processing.features import FEATURE_NAMES, PIPELINE_VERSION


def load_artifact(path):
    """Load a model only if it matches the SHA-256 recorded next to it when it was trained.

    joblib files are pickles: loading one runs arbitrary code, so an unrecorded or altered
    file is refused before it is unpickled. Only load models produced by `sentinel train`.
    """
    path = Path(path)
    sidecar = path.with_name(path.name + ".sha256")
    if not sidecar.is_file():
        raise ValueError(f"{path.name} has no recorded SHA-256 ({sidecar.name}); retrain the model")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != sidecar.read_text().strip():
        raise ValueError(f"{path.name} does not match its recorded SHA-256")
    return joblib.load(io.BytesIO(data))


class Inference:
    def __init__(self, path=None, allow_simulated=False):
        self.artifact = load_artifact(path) if path else None
        self.version = self.artifact["version"] if self.artifact else "threshold-demo-v1"
        if self.artifact and self.artifact["simulated"] and not allow_simulated:
            raise ValueError("synthetic model is forbidden for physical inference")
        if self.artifact and self.artifact["features"] != FEATURE_NAMES:
            raise ValueError("model feature schema differs from pipeline")
        if self.artifact and self.artifact["pipeline"] != PIPELINE_VERSION:
            raise ValueError("model was trained with a different feature pipeline version")

    def score(self, features):
        if self.artifact is None:
            # Engineering demo score, not a calibrated fault probability:
            # normalized two-sensor level disagreement, capped at 15 points.
            return min(1.0, features["level_agreement_abs_mean"] / 15.0)
        x = [[features[name] for name in FEATURE_NAMES]]
        model = self.artifact["model"]
        if self.artifact["kind"] == "isolation":
            return float(1 / (1 + np.exp(np.clip(model.decision_function(x)[0]*20, -50, 50))))
        probabilities = model.predict_proba(x)[0]
        normal = list(model.classes_).index("NORMAL")
        return float(1-probabilities[normal])

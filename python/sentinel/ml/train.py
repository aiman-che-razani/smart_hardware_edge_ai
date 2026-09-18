import hashlib
import json
from pathlib import Path
import time
import uuid
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, average_precision_score
from sentinel.storage.database import connect
from sentinel.processing.features import FEATURE_NAMES


def grouped_partitions(run_labels, seed=42):
    """Stratify whole runs; require >=3 independent runs per class."""
    rng = np.random.default_rng(seed)
    output = {"train": [], "validation": [], "test": []}
    for label in sorted(set(run_labels.values())):
        runs = sorted(r for r, c in run_labels.items() if c == label)
        if len(runs) < 3:
            raise ValueError(f"{label}: need at least 3 independent runs, preferably >=10")
        rng.shuffle(runs)
        n = max(1, round(len(runs)*0.2))
        output["test"].extend(runs[:n])
        output["validation"].extend(runs[n:2*n])
        output["train"].extend(runs[2*n:])
    return output


def dataset(root, simulated):
    with connect(root) as db:
        rows = db.execute("""SELECT f.*, r.condition, r.simulated, r.sampling_rate, r.metadata FROM feature_window f
        JOIN experiment_run r USING(run_id) WHERE r.status='COMPLETE' AND r.simulated=?
        ORDER BY f.run_id, f.timestamp""", (int(simulated),)).fetchall()
    rows = [dict(row) for row in rows]
    if not rows:
        raise ValueError("no completed feature runs for the selected data source")
    if any(r["condition"] == "CYCLE" for r in rows):
        raise ValueError("CYCLE demo runs are not labelled training runs; use a separate dataset directory")
    return rows


def arrays(rows, ids):
    subset = [r for r in rows if r["run_id"] in ids]
    x = np.array([[json.loads(r["features"])[k] for k in FEATURE_NAMES] for r in subset])
    y = np.array([r["condition"] for r in subset])
    return x, y


def metrics(y, predictions, risk):
    fault = y != "NORMAL"
    detected = np.asarray(predictions) != "NORMAL"
    labels = sorted(set(y) | set(predictions))
    return {"classification": classification_report(y, predictions, output_dict=True, zero_division=0),
            "labels": labels, "confusion_matrix": confusion_matrix(y, predictions, labels=labels).tolist(),
            "fault_recall": float(detected[fault].mean()) if fault.any() else None,
            "false_positive_rate": float(detected[~fault].mean()) if (~fault).any() else None,
            "missed_fault_windows": int(np.sum(fault & ~detected)),
            "roc_auc": float(roc_auc_score(fault, risk)) if len(set(fault)) == 2 else None,
            "pr_auc": float(average_precision_score(fault, risk)) if len(set(fault)) == 2 else None}


def train(root, output, simulated=False, seed=42):
    output = Path(output)
    if output.exists():
        raise ValueError("use a new output directory to preserve split/model provenance")
    rows = dataset(root, simulated)
    rates = {r["sampling_rate"] for r in rows}
    if len(rates) != 1:
        raise ValueError("do not mix sampling rates in one model")
    windows = {json.dumps(json.loads(r["metadata"])["window"],sort_keys=True) for r in rows}
    if len(windows) != 1:
        raise ValueError("do not mix window configurations in one model")
    labels = {r["run_id"]: r["condition"] for r in rows}
    if "NORMAL" not in labels.values() or len(set(labels.values())) < 2:
        raise ValueError("need NORMAL plus a fault condition")
    splits = grouped_partitions(labels, seed)
    x, y = arrays(rows, splits["train"])
    vx, vy = arrays(rows, splits["validation"])
    candidates = {
        "logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=seed)),
        "tree": DecisionTreeClassifier(max_depth=5, min_samples_leaf=2, random_state=seed),
        "forest": RandomForestClassifier(n_estimators=100, max_depth=8, min_samples_leaf=2, random_state=seed, n_jobs=1),
        "isolation": make_pipeline(StandardScaler(), IsolationForest(n_estimators=100, random_state=seed)),
    }
    reports = {}
    models = {}
    for name, model in candidates.items():
        model.fit(x[y == "NORMAL"] if name == "isolation" else x,
                  None if name == "isolation" else y)
        start = time.perf_counter()
        if name == "isolation":
            risk = 1/(1+np.exp(np.clip(model.decision_function(vx)*20, -50, 50)))
            predicted = np.where(risk >= 0.5, "ANOMALY", "NORMAL")
        else:
            predicted = model.predict(vx)
            risk = 1-model.predict_proba(vx)[:, list(model.classes_).index("NORMAL")]
        latency = (time.perf_counter()-start)*1000/len(vx)
        report = metrics(vy, predicted, risk)
        report["batch_ms_per_window"] = latency
        reports[name] = report
        models[name] = model
    threshold_risk = np.minimum(1, vx[:, FEATURE_NAMES.index("level_agreement_abs_mean")]/15.0)
    reports["threshold"] = metrics(vy, np.where(threshold_risk >= 0.8, "ANOMALY", "NORMAL"), threshold_risk)
    # Choose supervised candidate by fault recall, then false positives, then simpler model.
    chosen = max(("logistic", "tree", "forest"), key=lambda n: (
        reports[n]["fault_recall"], -reports[n]["false_positive_rate"], -["logistic", "tree", "forest"].index(n)))
    output.mkdir(parents=True)
    version = str(uuid.uuid4())
    artifact = {"version": version, "kind": chosen, "model": models[chosen], "features": FEATURE_NAMES,
                "simulated": simulated, "seed": seed, "splits": splits, "fs": rates.pop(),
                "dataset_sha256": hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),
                "window": json.loads(windows.pop()),
                "pipeline": "level-ambient-slope-v1"}
    joblib.dump(artifact, output / "model.joblib")
    (output / "splits.json").write_text(json.dumps(splits, indent=2))
    report = {"source": "SIMULATED" if simulated else "PHYSICAL", "selected": chosen,
              "selection": "validation fault recall, false positives, simplicity", "validation": reports,
              "test": "untouched; run evaluate once after selection", "version": version}
    (output / "report.json").write_text(json.dumps(report, indent=2))
    with connect(root) as db:
        db.execute("INSERT INTO model VALUES (?,?,?,?)", (version, time.time(), str(output / "model.joblib"), json.dumps(report)))
    return report


def evaluate(root, directory):
    directory = Path(directory)
    destination = directory / "test-report.json"
    if destination.exists():
        raise ValueError("test evaluation already recorded; preserve the held-out result")
    artifact = joblib.load(directory / "model.joblib")
    rows = dataset(root, artifact["simulated"])
    if hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest() != artifact["dataset_sha256"]:
        raise ValueError("dataset changed since split/model freeze; use the original dataset snapshot")
    x, y = arrays(rows, artifact["splits"]["test"])
    if not len(x):
        raise ValueError("held-out runs missing")
    model = artifact["model"]
    result = metrics(y, model.predict(x), 1-model.predict_proba(x)[:, list(model.classes_).index("NORMAL")])
    result.update(source="SIMULATED" if artifact["simulated"] else "PHYSICAL",
                  model_sha256=hashlib.sha256((directory / "model.joblib").read_bytes()).hexdigest())
    destination.write_text(json.dumps(result, indent=2))
    return result

"""Bounded host microbenchmark; generated input, not hardware latency."""
import json
from pathlib import Path
import time
import tracemalloc
import numpy as np
from sentinel.processing.features import extract, CHANNELS
from sentinel.ml.inference import Inference


def _window(size=30):
    return [{channel: 50.0 + i * 0.1 for channel in CHANNELS} for i in range(size)]


def profile(output, model=None, iterations=100):
    window=_window()
    inference=Inference(model,allow_simulated=True)
    timings={name:[] for name in ('features_ms','inference_ms')}
    extract(window,1) # warm imports/caches before timing
    tracemalloc.start()
    started=time.perf_counter(); cpu=time.process_time()
    for _ in range(iterations):
        start=time.perf_counter(); features=extract(window,1)
        timings['features_ms'].append((time.perf_counter()-start)*1000)
        start=time.perf_counter(); inference.score(features)
        timings['inference_ms'].append((time.perf_counter()-start)*1000)
    _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
    result={'source':'GENERATED MICROBENCHMARK','iterations':iterations,'model_version':inference.version,
            'wall_s':time.perf_counter()-started,'cpu_s':time.process_time()-cpu,
            'peak_traced_python_bytes':peak,
            'limitations':'Tracemalloc changes timing and does not measure total process RSS; no serial or hardware latency is included.',
            **{name:{'p50':float(np.median(v)),'p95':float(np.percentile(v,95))} for name,v in timings.items()}}
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2))
    return result

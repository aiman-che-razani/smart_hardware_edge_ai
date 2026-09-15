"""Bounded host microbenchmark; generated input, not hardware latency."""
import json
from pathlib import Path
import time
import tracemalloc
import numpy as np
from sentinel.processing.features import spectrum, extract
from sentinel.ml.inference import Inference


def profile(output, model=None, iterations=100):
    t=np.arange(800)/800
    values=np.column_stack([0.1*np.sin(2*np.pi*30*t),0.05*np.sin(2*np.pi*30*t),np.ones(800)])
    inference=Inference(model,allow_simulated=True)
    timings={name:[] for name in ('fft_ms','features_ms','inference_ms')}
    extract(values,800) # warm imports/caches before timing
    tracemalloc.start()
    started=time.perf_counter(); cpu=time.process_time()
    for _ in range(iterations):
        start=time.perf_counter(); spectrum(values[:,0],800)
        timings['fft_ms'].append((time.perf_counter()-start)*1000)
        start=time.perf_counter(); features=extract(values,800)
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

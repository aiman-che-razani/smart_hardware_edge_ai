import numpy as np
from scipy import signal

METRICS = ("rms", "peak_to_peak", "std", "variance", "skewness", "kurtosis", "crest_factor",
           "dominant_hz", "dominant_amplitude", "spectral_energy", "spectral_centroid",
           "band_0_50", "band_50_150", "band_150_nyquist", "harmonic_ratio")
FEATURE_NAMES = [f"{axis}_{name}" for axis in "xyz" for name in METRICS]


def highpass(values, fs, cutoff=5.0):
    if not 0 < cutoff < fs / 2:
        raise ValueError("cutoff outside Nyquist interval")
    return signal.sosfiltfilt(signal.butter(3, cutoff, btype="highpass", fs=fs, output="sos"), values, axis=0)


def spectrum(values, fs):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or len(x) < 8 or fs <= 0 or not np.isfinite(x).all():
        raise ValueError("spectrum requires >=8 finite samples and positive rate")
    window = signal.windows.hann(len(x), sym=False)
    fft = np.fft.rfft((x - x.mean()) * window)
    amplitude = np.abs(fft) / window.sum()
    psd = abs(fft) ** 2 / (fs * np.sum(window ** 2))
    endpoint = -1 if len(x) % 2 == 0 else None
    amplitude[1:endpoint] *= 2
    psd[1:endpoint] *= 2
    return np.fft.rfftfreq(len(x), 1 / fs), amplitude, psd


def extract(values, fs):
    x = np.asarray(values, dtype=float)
    if x.ndim != 2 or x.shape[1] != 3 or len(x) < 8 or not np.isfinite(x).all():
        raise ValueError("expected finite N x 3 acceleration")
    result = {}
    for axis, values in zip("xyz", x.T):
        y = values - values.mean()
        rms = float(np.sqrt(np.mean(y ** 2)))
        freq, amplitude, psd = spectrum(y, fs)
        power = psd * fs / len(y)
        total = float(power.sum())
        peak = int(np.argmax(amplitude[1:]) + 1) if rms > 1e-12 else 0
        dominant = float(freq[peak])
        harmonic = int(np.argmin(abs(freq - 2 * dominant)))
        metrics = [rms, float(np.ptp(y)), rms, rms*rms,
                   float(np.mean(y ** 3) / rms ** 3) if rms > 1e-12 else 0.0,
                   float(np.mean(y ** 4) / rms ** 4) if rms > 1e-12 else 0.0,
                   float(np.max(abs(y)) / rms) if rms > 1e-12 else 0.0,
                   dominant, float(amplitude[peak]), total,
                   float(np.dot(freq, power) / total) if total > 1e-24 else 0.0,
                   float(power[freq < 50].sum()), float(power[(freq >= 50) & (freq < 150)].sum()),
                   float(power[freq >= 150].sum()),
                   float(amplitude[harmonic] / amplitude[peak]) if peak and 2*dominant <= fs/2 else 0.0]
        result.update(zip((f"{axis}_{name}" for name in METRICS), metrics))
    return result

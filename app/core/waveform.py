"""Hitung puncak amplitudo (peaks) audio untuk digambar sebagai waveform."""
from typing import List, Tuple


def generate_peaks(audio_path: str, num_points: int = 3000) -> Tuple[List[float], int, int]:
    """Kembalikan (peaks_ternormalisasi_0..1, sample_rate, total_samples)."""
    import numpy as np
    import soundfile as sf

    data, sr = sf.read(audio_path, dtype="float32", always_2d=False)
    if data.ndim > 1:
        data = data.mean(axis=1)
    total_samples = len(data)
    if total_samples == 0:
        return [], sr, 0

    samples_per_point = max(1, total_samples // num_points)
    trimmed_len = (total_samples // samples_per_point) * samples_per_point
    if trimmed_len == 0:
        trimmed_len = total_samples
    usable = data[:trimmed_len] if trimmed_len else data
    if trimmed_len:
        reshaped = usable.reshape(-1, samples_per_point)
        peaks = np.abs(reshaped).max(axis=1)
    else:
        peaks = np.abs(data)

    peaks_list = peaks.tolist()
    max_peak = max(peaks_list) if peaks_list else 1.0
    if max_peak > 0:
        peaks_list = [p / max_peak for p in peaks_list]
    return peaks_list, int(sr), total_samples

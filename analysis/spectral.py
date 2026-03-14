from __future__ import annotations

from pathlib import Path
from typing import Any


def extract_spectral_metrics(audio_path: str | Path) -> dict[str, Any]:
    """
    Spectral & cepstral features:
    MFCC (1-4), spectral flux/centroid/slope.

    Formant/vowel-space placeholders are included for schema consistency.
    """
    try:
        import librosa
        import numpy as np
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing dependency 'librosa'. Install analysis/environment.yml."
        ) from exc

    y, sr = librosa.load(str(audio_path), sr=16000, mono=True)
    if y.size == 0:
        return {
            "mfcc_1_mean": 0.0,
            "mfcc_2_mean": 0.0,
            "mfcc_3_mean": 0.0,
            "mfcc_4_mean": 0.0,
            "spectral_flux_mean": 0.0,
            "spectral_centroid_mean": 0.0,
            "spectral_slope_mean": 0.0,
            "formant_f1_mean_hz": None,
            "formant_f2_mean_hz": None,
            "formant_f3_mean_hz": None,
            "vowel_space_area": None,
        }

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=4)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    flatness = librosa.feature.spectral_flatness(y=y)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)

    return {
        "mfcc_1_mean": float(np.mean(mfcc[0])),
        "mfcc_2_mean": float(np.mean(mfcc[1])),
        "mfcc_3_mean": float(np.mean(mfcc[2])),
        "mfcc_4_mean": float(np.mean(mfcc[3])),
        "spectral_flux_mean": float(np.mean(onset_env)),
        "spectral_centroid_mean": float(np.mean(centroid)),
        "spectral_slope_mean": float(np.mean(flatness)),
        "formant_f1_mean_hz": None,
        "formant_f2_mean_hz": None,
        "formant_f3_mean_hz": None,
        "vowel_space_area": None,
    }

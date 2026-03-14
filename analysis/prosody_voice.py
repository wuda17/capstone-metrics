from __future__ import annotations

from pathlib import Path
from typing import Any

from .audio_utils import temporary_standardized_wav


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        out = float(value)
        if out != out or out in (float("inf"), float("-inf")):
            return None
        return out
    except (TypeError, ValueError):
        return None


def extract_prosody_voice_metrics(
    audio_path: str | Path,
    opensmile_extractor: Any | None = None,
) -> dict[str, Any]:
    """
    Prosody & voice quality metrics:
    F0, jitter, shimmer, HNR, CPP (if available in extractor output).
    """
    try:
        import parselmouth
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing dependency 'praat-parselmouth'. Install analysis/environment.yml."
        ) from exc

    with temporary_standardized_wav(audio_path) as std_path:
        snd = parselmouth.Sound(str(std_path))
        pitch = snd.to_pitch()
        harmonicity = snd.to_harmonicity_cc()
        point_process = parselmouth.praat.call(
            snd, "To PointProcess (periodic, cc)", 75, 500
        )
        jitter_local = parselmouth.praat.call(
            point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3
        )
        shimmer_local_db = parselmouth.praat.call(
            [snd, point_process], "Get shimmer (local_dB)", 0, 0, 0.0001, 0.02, 1.3, 1.6
        )

        f0_mean = _to_float(parselmouth.praat.call(pitch, "Get mean", 0, 0, "Hertz"))
        f0_min = _to_float(parselmouth.praat.call(pitch, "Get minimum", 0, 0, "Hertz", "Parabolic"))
        f0_max = _to_float(parselmouth.praat.call(pitch, "Get maximum", 0, 0, "Hertz", "Parabolic"))
        f0_std = _to_float(parselmouth.praat.call(pitch, "Get standard deviation", 0, 0, "Hertz"))
        hnr_db = _to_float(parselmouth.praat.call(harmonicity, "Get mean", 0, 0))

        cpp = None
        if opensmile_extractor is not None:
            try:
                smile_df = opensmile_extractor.process_file(str(std_path))
                row = smile_df.iloc[0].to_dict()
                cpp = _to_float(row.get("spectralFlux_sma3_amean"))  # best-effort placeholder key
            except Exception:
                cpp = None

        return {
            "f0_mean_hz": f0_mean,
            "f0_std_hz": f0_std,
            "f0_range_hz": (
                round(float(f0_max) - float(f0_min), 4)
                if f0_max is not None and f0_min is not None
                else None
            ),
            "jitter_local": _to_float(jitter_local),
            "shimmer_local_db": _to_float(shimmer_local_db),
            "hnr_db": hnr_db,
            "cpp": cpp,
        }


from __future__ import annotations

from pathlib import Path
from typing import Any

from .audio_utils import build_opensmile_extractor
from .prosody_voice import extract_prosody_voice_metrics
from .spectral import extract_spectral_metrics


def extract_acoustic_metrics(
    audio_path: str | Path,
    opensmile_extractor: Any | None = None,
    include_spectral: bool = True,
) -> dict[str, Any]:
    """
    Unified acoustic extraction:
    - Prosody/voice metrics (parselmouth + optional opensmile)
    - Spectral/cepstral metrics (librosa) when enabled/available
    """
    extractor = opensmile_extractor or build_opensmile_extractor()
    prosody = extract_prosody_voice_metrics(audio_path, opensmile_extractor=extractor)

    spectral: dict[str, Any] = {}
    if include_spectral:
        try:
            spectral = extract_spectral_metrics(audio_path)
        except Exception:
            spectral = {}

    return {
        "prosody": prosody,
        "spectral": spectral,
    }

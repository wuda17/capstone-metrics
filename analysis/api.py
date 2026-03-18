from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from .audio_utils import (
    build_opensmile_extractor,
    load_and_standardize,
    validate_audio,
)
from .interfaces import WordTiming
from .lexical_semantic import extract_lexical_semantic_metrics
from .prosody_voice import extract_prosody_voice_metrics
from .spectral import extract_spectral_metrics
from .temporal import extract_temporal_metrics

if TYPE_CHECKING:
    from .transcription import Transcriber


def prepare_audio(audio_path: str | Path) -> tuple[Any, int]:
    """Load + standardize audio. Input: path, Output: (audio, sample_rate)."""
    return load_and_standardize(audio_path)


def validate_prepared_audio(audio: Any, sample_rate: int) -> dict[str, Any]:
    """Validate already-loaded audio. Input: audio+sr, Output: validation dict."""
    return validate_audio(audio, sample_rate)


def transcribe_audio(
    audio_path: str | Path,
    speaker: str = "user",
    transcriber: "Transcriber | None" = None,
    model_size: str = "base",
) -> dict[str, Any]:
    """
    Transcribe audio. Input: path, Output: plain transcription payload dict.

    Pass an initialized `transcriber` for efficiency in loops/services.
    """
    if transcriber is None:
        from .transcription import Transcriber as _Transcriber

        engine = _Transcriber(model_size=model_size)
    else:
        engine = transcriber
    return engine.transcribe_payload(str(audio_path), speaker=speaker)


def compute_linguistic_metrics(
    text: str,
    words: list[WordTiming],
    duration_sec: float,
) -> dict[str, Any]:
    """Compute linguistic outputs grouped by source module."""
    temporal = extract_temporal_metrics(words, duration_sec=duration_sec, min_pause=0.1)
    lexical = extract_lexical_semantic_metrics(text)
    return {
        "temporal": temporal,
        "lexical": lexical,
    }


def compute_acoustic_metrics(
    audio_path: str | Path,
    opensmile_extractor: Any | None = None,
    include_spectral: bool = True,
) -> dict[str, Any]:
    """Compute acoustic metrics from a source audio file path.

    Runs two extraction passes over a single standardized WAV:
    - prosody/voice: F0 stats, jitter, shimmer, HNR, CPP via parselmouth
      and optionally OpenSMILE (eGeMAPS functionals).
    - spectral/cepstral: MFCC 1-4, spectral flux/centroid/slope via librosa,
      included by default and silently skipped if librosa is unavailable.

    Args:
        audio_path: Path to the source audio file.
        opensmile_extractor: Optional pre-built OpenSMILE Smile instance.
            If None, one is built lazily; pass an instance when processing
            multiple files to avoid repeated initialisation.
        include_spectral: Set False to skip the librosa spectral pass.
    """
    extractor = opensmile_extractor
    if extractor is None:
        try:
            extractor = build_opensmile_extractor()
        except RuntimeError:
            extractor = None

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

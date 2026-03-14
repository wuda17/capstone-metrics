from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from .audio_utils import (
    load_and_standardize,
    validate_audio,
)
from .acoustic import extract_acoustic_metrics as _extract_acoustic_metrics
from .interfaces import WordTiming
from .lexical_semantic import extract_lexical_semantic_metrics
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
    """Compute lexical + temporal metrics from transcript text + timings."""
    temporal = extract_temporal_metrics(words, duration_sec=duration_sec, min_pause=0.1)
    lexical = extract_lexical_semantic_metrics(text)
    return {
        **temporal,
        "type_token_ratio": lexical.get("type_token_ratio", 0.0),
        "self_focus_ratio": lexical.get("self_focus_ratio", 0.0),
        "filler_word_count": lexical.get("filler_word_count", 0),
        "sentiment_polarity": lexical.get("sentiment_polarity", 0.0),
    }


def compute_acoustic_metrics(
    audio_path: str | Path,
    opensmile_extractor: Any | None = None,
) -> dict[str, Any]:
    """Compute acoustic metrics from a source audio file path."""
    return _extract_acoustic_metrics(
        audio_path, opensmile_extractor=opensmile_extractor
    )

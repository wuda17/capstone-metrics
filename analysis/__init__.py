"""Public API for speech-analysis helpers used by services and demos."""

from __future__ import annotations

# Shared interfaces
from .interfaces import AnalysisBackend, TranscriptionPayload, WordTiming

# Core audio IO
from .audio_utils import (
    STANDARD_SAMPLE_RATE,
    build_opensmile_extractor,
    extract_and_forget,
    load_and_standardize,
    load_audio,
    normalize_amplitude,
    process_with_privacy_gate,
    save_standardized,
    temporary_standardized_wav,
    to_wav_bytes,
    validate_audio,
)

# Temporal & fluency metrics
from .temporal import (
    Pause,
    SessionMetrics,
    UtteranceMetrics,
    Word,
    calculate_pauses,
    classify_pause,
    compute_utterance_metrics,
    extract_temporal_metrics,
    normalize_words,
    percent_silence_duration,
    phonation_to_time_ratio,
    response_latency,
    speech_rate,
    words_to_payload,
)

# Lexical & semantic metrics
from .lexical_semantic import (
    extract_lexical_semantic_metrics,
    filler_word_count,
    self_focus_ratio,
    sentiment_polarity,
    tokenize_text,
    type_token_ratio,
)

# Prosody/voice and spectral/cepstral metrics
from .prosody_voice import extract_prosody_voice_metrics
from .spectral import extract_spectral_metrics
from .acoustic import extract_acoustic_metrics

try:
    from .transcription import Transcriber, log_transcription
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Transcriber = None  # type: ignore[assignment]

    def log_transcription(*args, **kwargs):  # type: ignore[no-redef]
        raise RuntimeError("Transcription features require 'openai-whisper'.")


try:
    from .api import (
        compute_acoustic_metrics,
        compute_linguistic_metrics,
        prepare_audio,
        transcribe_audio,
        validate_prepared_audio,
    )
except ModuleNotFoundError:  # pragma: no cover - optional dependency

    def prepare_audio(*args, **kwargs):  # type: ignore[no-redef]
        raise RuntimeError("Audio/transcription dependencies are not installed.")

    def validate_prepared_audio(*args, **kwargs):  # type: ignore[no-redef]
        raise RuntimeError("Audio/transcription dependencies are not installed.")

    def transcribe_audio(*args, **kwargs):  # type: ignore[no-redef]
        raise RuntimeError("Transcription features require 'openai-whisper'.")

    def compute_linguistic_metrics(*args, **kwargs):  # type: ignore[no-redef]
        raise RuntimeError("Audio/transcription dependencies are not installed.")

    def compute_acoustic_metrics(*args, **kwargs):  # type: ignore[no-redef]
        raise RuntimeError("Acoustic dependencies are not installed.")


try:
    from .pipeline import DefaultAnalysisBackend, build_default_analysis_backend
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    DefaultAnalysisBackend = None  # type: ignore[assignment]

    def build_default_analysis_backend(*args, **kwargs):  # type: ignore[no-redef]
        raise RuntimeError("Default analysis backend dependencies are not installed.")


__all__ = [
    # Preferred function-first API
    "prepare_audio",
    "validate_prepared_audio",
    "transcribe_audio",
    "compute_linguistic_metrics",
    "compute_acoustic_metrics",
    # Backend interface for services
    "AnalysisBackend",
    "DefaultAnalysisBackend",
    "build_default_analysis_backend",
    "WordTiming",
    "TranscriptionPayload",
    # Data structures
    "Word",
    "Pause",
    "UtteranceMetrics",
    "SessionMetrics",
    # Transcription helpers
    "Transcriber",
    "log_transcription",
    # Temporal & fluency
    "classify_pause",
    "normalize_words",
    "speech_rate",
    "calculate_pauses",
    "percent_silence_duration",
    "phonation_to_time_ratio",
    "response_latency",
    "extract_temporal_metrics",
    # Lexical & semantic
    "tokenize_text",
    "type_token_ratio",
    "self_focus_ratio",
    "filler_word_count",
    "sentiment_polarity",
    "extract_lexical_semantic_metrics",
    # Prosody/voice + spectral/cepstral
    "extract_prosody_voice_metrics",
    "extract_spectral_metrics",
    # Audio utilities
    "load_audio",
    "load_and_standardize",
    "normalize_amplitude",
    "to_wav_bytes",
    "save_standardized",
    "temporary_standardized_wav",
    "process_with_privacy_gate",
    "extract_and_forget",
    "build_opensmile_extractor",
    "extract_acoustic_metrics",
    "validate_audio",
    "STANDARD_SAMPLE_RATE",
    # Functional marker helpers
    "compute_utterance_metrics",
    "words_to_payload",
]

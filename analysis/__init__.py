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
    Word,
    calculate_pauses,
    classify_pause,
    extract_temporal_metrics,
    normalize_words,
    percent_silence_duration,
    phonation_to_time_ratio,
    response_latency,
    speech_rate,
)

# Lexical & semantic metrics
from .lexical_semantic import (
    emotion_score,
    extract_lexical_semantic_metrics,
    filler_word_count,
    self_pronoun_ratio,
    sentiment_polarity,
    tokenize_text,
    type_token_ratio,
)

# Prosody/voice and spectral/cepstral metrics
from .prosody_voice import extract_prosody_voice_metrics
from .spectral import extract_spectral_metrics


from .transcription import Transcriber

from .api import (
    compute_acoustic_metrics,
    compute_linguistic_metrics,
    prepare_audio,
    transcribe_audio,
    validate_prepared_audio,
)

from .pipeline import DefaultAnalysisBackend, build_default_analysis_backend

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
    # Transcription helpers
    "Transcriber",
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
    "self_pronoun_ratio",
    "emotion_score",
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
]

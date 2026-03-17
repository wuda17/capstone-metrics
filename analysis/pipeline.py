from __future__ import annotations

from pathlib import Path
from typing import Any

from .interfaces import AnalysisBackend, TranscriptionPayload
from .api import (
    compute_acoustic_metrics,
    compute_linguistic_metrics,
    prepare_audio,
    transcribe_audio,
    validate_prepared_audio,
)
from .audio_utils import build_opensmile_extractor


class DefaultAnalysisBackend:
    """Default implementation backed by current analysis modules."""

    def __init__(self, whisper_model: str = "base"):
        from .transcription import Transcriber

        self.whisper_model = whisper_model
        self.transcriber = Transcriber(model_size=whisper_model)
        self.opensmile_extractor = build_opensmile_extractor()

    def prepare_audio(self, audio_path: str | Path) -> tuple[Any, int]:
        return prepare_audio(audio_path)

    def validate_prepared_audio(self, audio: Any, sample_rate: int) -> dict[str, Any]:
        return validate_prepared_audio(audio, sample_rate)

    def transcribe_audio(
        self, audio_path: str | Path, speaker: str = "user"
    ) -> dict[str, Any]:
        return transcribe_audio(
            audio_path,
            speaker=speaker,
            transcriber=self.transcriber,
            model_size=self.whisper_model,
        )

    def compute_acoustic_metrics(self, *, audio_path: str | Path) -> dict[str, Any]:
        return compute_acoustic_metrics(
            audio_path,
            opensmile_extractor=self.opensmile_extractor,
        )

    def calculate(
        self,
        *,
        audio_path: str | Path,
        transcription: TranscriptionPayload,
        duration_sec: float,
    ) -> dict[str, dict[str, Any]]:
        outputs: dict[str, dict[str, Any]] = {}

        outputs["linguistic"] = compute_linguistic_metrics(
            text=transcription["text"],
            words=transcription["words"],
            duration_sec=duration_sec,
        )

        outputs["acoustic"] = self.compute_acoustic_metrics(audio_path=audio_path)

        return outputs


def build_default_analysis_backend(whisper_model: str = "base") -> AnalysisBackend:
    return DefaultAnalysisBackend(whisper_model=whisper_model)

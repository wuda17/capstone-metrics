from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, TypedDict


class WordTiming(TypedDict, total=False):
    word: str
    start: float
    end: float
    conf: float


class TranscriptionPayload(TypedDict):
    speaker: str
    timestamp: str
    text: str
    words: list[WordTiming]
    metrics: dict[str, Any]


class AnalysisBackend(Protocol):
    """Interface consumed by `localhost_demo/services/metrics_service.py`."""

    def prepare_audio(self, audio_path: str | Path) -> tuple[Any, int]:
        ...

    def validate_prepared_audio(self, audio: Any, sample_rate: int) -> dict[str, Any]:
        ...

    def transcribe_audio(self, audio_path: str | Path, speaker: str = "user") -> TranscriptionPayload:
        ...

    def compute_linguistic_metrics(
        self,
        transcript_text: str,
        words: list[WordTiming],
        duration_sec: float,
    ) -> dict[str, Any]:
        ...

    def compute_acoustic_metrics(self, audio_path: str | Path) -> dict[str, Any]:
        ...


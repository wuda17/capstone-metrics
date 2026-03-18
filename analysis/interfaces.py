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
    """Interface consumed by `localhost_demo/services/metrics_service.py`.

    Only the four methods actually called by the service are required here.
    Implementations are free to expose additional helpers internally.
    """

    def prepare_audio(self, audio_path: str | Path) -> tuple[Any, int]: ...

    def validate_prepared_audio(
        self, audio: Any, sample_rate: int
    ) -> dict[str, Any]: ...

    def transcribe_audio(
        self, audio_path: str | Path, speaker: str = "user"
    ) -> TranscriptionPayload: ...

    def calculate(
        self,
        *,
        audio_path: str | Path,
        transcription: TranscriptionPayload,
        duration_sec: float,
    ) -> dict[str, dict[str, Any]]: ...

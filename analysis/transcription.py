"""
Transcription Module
--------------------
Whisper transcription with word-level timestamps.

Features:
- Word-level timestamp extraction
- Optional async wrappers
- Configurable Whisper model size

Usage:
    from speech_analysis.transcription import Transcriber

    transcriber = Transcriber(model_size="small")

    # Sync usage
    payload = transcriber.transcribe_payload("audio.wav", speaker="user")

    # Async usage
    metrics = await transcriber.transcribe_async("audio.wav", speaker="user")
"""

import asyncio
from datetime import datetime
from typing import Any, Optional

import whisper

from .interfaces import TranscriptionPayload


class Transcriber:
    """
    Whisper-based transcriber returning plain payload dictionaries.
    """

    def __init__(self, model_size: str = "small"):
        """
        Initialize transcriber with Whisper model.

        Args:
            model_size: Whisper model size - "tiny", "base", "small",
                       "medium", or "large" (default: "small")
        """
        self.model = whisper.load_model(model_size)
        self.model_size = model_size

    @staticmethod
    def _empty_payload(speaker: str) -> TranscriptionPayload:
        return {
            "speaker": speaker,
            "timestamp": datetime.now().isoformat(),
            "text": "",
            "words": [],
            "metrics": {},
        }

    @staticmethod
    def _extract_words(result: dict[str, Any]) -> list[dict[str, Any]]:
        words: list[dict[str, Any]] = []
        for segment in result.get("segments", []):
            for w in segment.get("words", []):
                words.append(
                    {
                        "word": str(w.get("word", "")).strip(),
                        "start": float(w.get("start", 0.0)),
                        "end": float(w.get("end", 0.0)),
                        "conf": float(w.get("probability", 1.0)),
                    }
                )
        return words

    def transcribe_payload(
        self, wav_path: str, speaker: str = "user"
    ) -> TranscriptionPayload:
        """
        Transcribe audio into plain dictionary payload.

        Returns a function-friendly result shape:
        {'text', 'words', 'speaker', 'timestamp', 'metrics'}
        """
        try:
            result = self.model.transcribe(wav_path, word_timestamps=True)
            text = (result.get("text") or "").strip()
            raw_words = self._extract_words(result)

            timestamp = datetime.now().isoformat()
            if not text:
                return self._empty_payload(speaker)

            return {
                "speaker": speaker,
                "timestamp": timestamp,
                "text": text,
                "words": raw_words,
                "metrics": {},
            }
        except Exception as e:
            print(f"[Transcriber] ⚠️ Transcription error: {e}")
            return self._empty_payload(speaker)

    def transcribe(
        self, wav_path: str, speaker: str = "user"
    ) -> Optional[dict[str, Any]]:
        return self.transcribe_or_none(wav_path, speaker=speaker)

    def transcribe_or_none(
        self,
        wav_path: str,
        speaker: str = "user",
    ) -> Optional[dict[str, Any]]:
        payload = self.transcribe_payload(wav_path, speaker=speaker)
        if not payload["text"]:
            return None
        return payload

    async def transcribe_async(
        self, wav_path: str, speaker: str = "user"
    ) -> Optional[dict[str, Any]]:
        """
        Async version of transcribe() for use in async pipelines.

        Runs the Whisper model in a thread pool to avoid blocking
        the event loop.

        Args:
            wav_path: Path to WAV file
            speaker: Speaker identifier

        Returns:
            Transcription payload dict, or None
        """
        return await asyncio.to_thread(self.transcribe, wav_path, speaker)

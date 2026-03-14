"""
Temporal & Fluency Metrics
--------------------------
Processing speed and flow metrics from timestamped words.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from typing import Any
from statistics import median

from .lexical_semantic import extract_lexical_semantic_metrics


def speech_rate(word_count: int, total_duration_seconds: float) -> float:
    """
    Calculate speech rate in words per minute (WPM).

    Words per minute over total duration.
    """
    if total_duration_seconds <= 0:
        return 0.0

    minutes = total_duration_seconds / 60.0
    return word_count / minutes


SIGNIFICANT_PAUSE_THRESHOLD = 0.5


def _coerce_word(word: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Coerce a mapping/object word into {'word','start','end'} shape."""
    if isinstance(word, Mapping):
        text = str(word.get("word", "")).strip()
        start = float(word.get("start", 0.0))
        end = float(word.get("end", start))
        return {"word": text, "start": start, "end": end}

    text = str(getattr(word, "word", "")).strip()
    start = float(getattr(word, "start", 0.0))
    end = float(getattr(word, "end", start))
    return {"word": text, "start": start, "end": end}


def normalize_words(words: Sequence[Mapping[str, Any] | Any]) -> list[dict[str, Any]]:
    """Normalize mixed word inputs into a plain dict list."""
    out: list[dict[str, Any]] = []
    for word in words:
        normalized = _coerce_word(word)
        if not normalized["word"]:
            continue
        out.append(normalized)
    return out


def classify_pause(duration: float) -> str:
    """Classify pause duration into short/medium/long buckets."""
    if duration > 1.0:
        return "long"
    if duration > 0.5:
        return "medium"
    return "short"


def calculate_pauses(
    words: Sequence[Mapping[str, Any] | Any],
    min_pause: float = SIGNIFICANT_PAUSE_THRESHOLD,
) -> list[dict[str, Any]]:
    """
    Identify pauses between adjacent words.
    """
    normalized_words = normalize_words(words)
    pauses: list[dict[str, Any]] = []

    for i in range(1, len(normalized_words)):
        prev = normalized_words[i - 1]
        curr = normalized_words[i]
        prev_end = prev["end"]
        curr_start = curr["start"]
        gap = curr_start - prev_end

        if gap >= min_pause:
            pauses.append(
                {
                    "after_word": prev["word"],
                    "before_word": curr["word"],
                    "start": round(prev_end, 3),
                    "end": round(curr_start, 3),
                    "duration": round(gap, 3),
                    "pause_type": classify_pause(gap),
                }
            )

    return pauses


def pause_statistics(
    words: Sequence[Mapping[str, Any] | Any],
    duration_sec: float,
    min_pause: float = 0.1,
) -> dict[str, Any]:
    pauses = calculate_pauses(words, min_pause=min_pause)
    durations = [float(p["duration"]) for p in pauses]
    total_pause = sum(durations)
    return {
        "pause_count": len(pauses),
        "pause_rate_per_min": (
            round((len(pauses) / duration_sec) * 60.0, 3) if duration_sec > 0 else 0.0
        ),
        "total_pause_time_sec": round(total_pause, 3),
        "mean_pause_duration_sec": (
            round(total_pause / len(pauses), 3) if pauses else 0.0
        ),
        "median_pause_duration_sec": round(median(durations), 3) if pauses else 0.0,
        "long_pauses": sum(1 for p in pauses if p.get("pause_type") == "long"),
        "medium_pauses": sum(1 for p in pauses if p.get("pause_type") == "medium"),
        "short_pauses": sum(1 for p in pauses if p.get("pause_type") == "short"),
        "pauses": pauses,
    }


def articulation_rate(
    words: Sequence[Mapping[str, Any] | Any],
    duration_sec: float,
    min_pause: float = 0.1,
) -> float:
    normalized = normalize_words(words)
    if not normalized or duration_sec <= 0:
        return 0.0
    pauses = calculate_pauses(normalized, min_pause=min_pause)
    pause_total = sum(float(p["duration"]) for p in pauses)
    voiced_duration = max(0.0, duration_sec - pause_total)
    return (
        round((len(normalized) / voiced_duration) * 60.0, 3)
        if voiced_duration > 0
        else 0.0
    )


def phonation_to_time_ratio(
    words: Sequence[Mapping[str, Any] | Any],
    duration_sec: float,
) -> float:
    normalized = normalize_words(words)
    if not normalized or duration_sec <= 0:
        return 0.0
    voiced_time = sum(max(0.0, float(w["end"]) - float(w["start"])) for w in normalized)
    return round(voiced_time / duration_sec, 4)


def response_latency(prev_turn_end: float, current_turn_start: float) -> float:
    return max(0.0, round(current_turn_start - prev_turn_end, 3))


# -----------------------------------------------------------------------------
# Combined Metrics Extraction
# -----------------------------------------------------------------------------


def extract_temporal_metrics(
    words: Sequence[Mapping[str, Any] | Any],
    duration_sec: float | None = None,
    min_pause: float = 0.1,
) -> dict[str, Any]:
    normalized_words = normalize_words(words)
    if duration_sec is None:
        duration_sec = (
            max(0.0, normalized_words[-1]["end"] - normalized_words[0]["start"])
            if normalized_words
            else 0.0
        )
    pause_stats = pause_statistics(
        normalized_words, float(duration_sec), min_pause=min_pause
    )
    return {
        "word_count": len(normalized_words),
        "duration_sec": round(float(duration_sec), 3),
        "speech_rate_wpm": round(
            speech_rate(len(normalized_words), float(duration_sec)), 1
        ),
        "articulation_rate_wpm": articulation_rate(
            normalized_words, float(duration_sec), min_pause=min_pause
        ),
        "phonation_to_time_ratio": phonation_to_time_ratio(
            normalized_words, float(duration_sec)
        ),
        **pause_stats,
    }


def extract_linguistic_metrics(
    transcript_text: str,  # kept for compatibility
    words: Sequence[Mapping[str, Any] | Any],
    duration_sec: float | None = None,
    min_pause: float = 0.1,
) -> dict[str, Any]:
    _ = transcript_text
    return extract_temporal_metrics(
        words, duration_sec=duration_sec, min_pause=min_pause
    )


def percent_silence_duration(
    words: Sequence[Mapping[str, Any] | Any],
    total_sample_time: float,
) -> tuple[float, float, list[dict[str, Any]]]:
    if not words or total_sample_time <= 0:
        return 0.0, 0.0, []
    pauses = calculate_pauses(words, min_pause=SIGNIFICANT_PAUSE_THRESHOLD)
    total_pause_duration = sum(float(p["duration"]) for p in pauses)
    psd_percent = (total_pause_duration / total_sample_time) * 100
    return round(psd_percent, 2), round(total_pause_duration, 3), pauses


def extract_all_metrics(
    transcript_text: str,
    words: Sequence[Mapping[str, Any] | Any],
    total_sample_time: float,
) -> dict[str, Any]:
    _ = transcript_text
    base = extract_temporal_metrics(words, duration_sec=total_sample_time)
    psd_percent, pause_duration, pauses = percent_silence_duration(
        words, total_sample_time
    )
    return {
        **base,
        "total_pause_duration": pause_duration,
        "percent_silence_duration": psd_percent,
        "significant_pauses": pauses,
    }


# -----------------------------------------------------------------------------
# Session/Utterance Metric Containers
# -----------------------------------------------------------------------------


@dataclass
class Word:
    """A single recognized word with timing (audio-stream time)."""

    word: str
    start: float
    end: float
    conf: float = 1.0


@dataclass
class Pause:
    """A pause between words."""

    after_word: str
    before_word: str
    start: float
    end: float
    duration: float
    pause_type: str  # "short", "medium", "long"


@dataclass
class UtteranceMetrics:
    """Cognitive metrics for a single utterance."""

    speaker: str
    timestamp: str
    text: str
    words: list[Word] = field(default_factory=list)
    pauses: list[Pause] = field(default_factory=list)

    # Computed metrics
    word_count: int = 0
    type_token_ratio: float = 0.0
    duration: float = 0.0
    speech_rate_wpm: float = 0.0
    pause_count: int = 0
    total_pause_time: float = 0.0
    mean_pause_duration: float = 0.0
    long_pauses: int = 0
    medium_pauses: int = 0
    short_pauses: int = 0

    def compute_metrics(self) -> None:
        """Compute metrics from transcript text + word timings."""
        payload = compute_utterance_metrics(
            text=self.text,
            words=self.words,
            speaker=self.speaker,
            timestamp=self.timestamp,
        )
        self.word_count = int(payload["word_count"])
        self.type_token_ratio = float(payload["type_token_ratio"])
        self.duration = float(payload["duration_sec"])
        self.speech_rate_wpm = float(payload["speech_rate_wpm"])
        self.pause_count = int(payload["pause_count"])
        self.total_pause_time = float(payload["total_pause_time_sec"])
        self.mean_pause_duration = float(payload["mean_pause_duration_sec"])
        self.long_pauses = int(payload["long_pauses"])
        self.medium_pauses = int(payload["medium_pauses"])
        self.short_pauses = int(payload["short_pauses"])
        self.pauses = [
            Pause(
                after_word=str(p.get("after_word", "")),
                before_word=str(p.get("before_word", "")),
                start=float(p.get("start", 0.0)),
                end=float(p.get("end", 0.0)),
                duration=float(p.get("duration", 0.0)),
                pause_type=str(p.get("pause_type", "short")),
            )
            for p in payload.get("pauses", [])
        ]

    def to_dict(self) -> dict[str, Any]:
        """Export as dictionary."""
        return {
            "speaker": self.speaker,
            "timestamp": self.timestamp,
            "text": self.text,
            "word_count": self.word_count,
            "type_token_ratio": self.type_token_ratio,
            "duration": round(self.duration, 3),
            "speech_rate_wpm": self.speech_rate_wpm,
            "pause_count": self.pause_count,
            "total_pause_time": round(self.total_pause_time, 3),
            "mean_pause_duration": self.mean_pause_duration,
            "long_pauses": self.long_pauses,
            "medium_pauses": self.medium_pauses,
            "short_pauses": self.short_pauses,
            "words": [asdict(w) for w in self.words],
            "pauses": [asdict(p) for p in self.pauses],
        }


@dataclass
class SessionMetrics:
    """Aggregated metrics for an entire session."""

    session_start: str = ""
    utterances: list[UtteranceMetrics] = field(default_factory=list)

    def add_utterance(self, metrics: UtteranceMetrics) -> None:
        self.utterances.append(metrics)

    def get_user_metrics(self) -> list[UtteranceMetrics]:
        return [u for u in self.utterances if u.speaker == "user"]

    def get_summary(self) -> dict[str, Any]:
        user_utterances = self.get_user_metrics()
        if not user_utterances:
            return {}

        total_words = sum(u.word_count for u in user_utterances)
        total_duration = sum(u.duration for u in user_utterances)
        total_pauses = sum(u.pause_count for u in user_utterances)
        total_pause_time = sum(u.total_pause_time for u in user_utterances)
        ttr_values = [
            u.type_token_ratio for u in user_utterances if u.type_token_ratio > 0
        ]
        avg_ttr = round(sum(ttr_values) / len(ttr_values), 4) if ttr_values else 0.0

        return {
            "session_start": self.session_start,
            "utterance_count": len(user_utterances),
            "total_words": total_words,
            "avg_type_token_ratio": avg_ttr,
            "total_speech_duration": round(total_duration, 3),
            "avg_speech_rate_wpm": (
                round(total_words / (total_duration / 60), 1)
                if total_duration > 0
                else 0
            ),
            "total_pauses": total_pauses,
            "total_pause_time": round(total_pause_time, 3),
            "avg_pause_duration": (
                round(total_pause_time / total_pauses, 3) if total_pauses > 0 else 0
            ),
            "long_pauses": sum(u.long_pauses for u in user_utterances),
            "medium_pauses": sum(u.medium_pauses for u in user_utterances),
            "short_pauses": sum(u.short_pauses for u in user_utterances),
        }

    def to_json(self) -> dict[str, Any]:
        return {
            "summary": self.get_summary(),
            "utterances": [u.to_dict() for u in self.utterances],
        }

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_json(), handle, indent=2, ensure_ascii=False)
        print(f"[Metrics] Saved cognitive metrics to {path}")

    def print_summary(self) -> None:
        summary = self.get_summary()
        if not summary:
            print("[Metrics] No cognitive metrics collected this session.")
            return

        print("\n" + "=" * 50)
        print("SESSION COGNITIVE SUMMARY")
        print("=" * 50)
        print(f"Utterances:           {summary.get('utterance_count', 0)}")
        print(f"Total Words:          {summary.get('total_words', 0)}")
        print(f"Avg TTR (Lexical):    {summary.get('avg_type_token_ratio', 0):.4f}")
        print(f"Avg Speech Rate:      {summary.get('avg_speech_rate_wpm', 0):.1f} wpm")
        print("=" * 50)
        print("PAUSE ANALYSIS")
        print("=" * 50)
        print(f"Total Pauses:         {summary.get('total_pauses', 0)}")
        print(f"Avg Pause Duration:   {summary.get('avg_pause_duration', 0):.3f}s")
        print(f"  - Long (>1s):       {summary.get('long_pauses', 0)}")
        print(f"  - Medium (0.5-1s):  {summary.get('medium_pauses', 0)}")
        print(f"  - Short (0.1-0.5s): {summary.get('short_pauses', 0)}")


def words_to_payload(words: list[Word] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Word dataclasses (or dicts) into normalized dict payloads."""
    out: list[dict[str, Any]] = []
    for word in words:
        if isinstance(word, Word):
            out.append(asdict(word))
        elif isinstance(word, dict):
            out.append(word)

    normalized: list[dict[str, Any]] = []
    for word in out:
        token = str(word.get("word", "")).strip()
        if not token:
            continue
        start = float(word.get("start", 0.0))
        end = float(word.get("end", start))
        normalized.append(
            {
                "word": token,
                "start": start,
                "end": end,
                "conf": float(word.get("conf", 1.0)),
            }
        )
    return normalized


def compute_utterance_metrics(
    text: str,
    words: list[Word] | list[dict[str, Any]],
    speaker: str = "user",
    timestamp: str | None = None,
) -> dict[str, Any]:
    """
    Function-first API: text + words in, unified metrics dict out.

    The output shape remains compatible with existing callers while delegating
    actual metric extraction to specialized modules.
    """
    normalized = words_to_payload(words)
    temporal = extract_temporal_metrics(normalized, duration_sec=None, min_pause=0.1)
    lexical = extract_lexical_semantic_metrics(text)
    return {
        "speaker": speaker,
        "timestamp": timestamp or datetime.now().isoformat(),
        "text": text,
        "word_count": int(temporal.get("word_count", 0)),
        "type_token_ratio": float(lexical.get("type_token_ratio", 0.0)),
        "duration_sec": float(temporal.get("duration_sec", 0.0)),
        "speech_rate_wpm": float(temporal.get("speech_rate_wpm", 0.0)),
        "pause_count": int(temporal.get("pause_count", 0)),
        "total_pause_time_sec": float(temporal.get("total_pause_time_sec", 0.0)),
        "mean_pause_duration_sec": float(temporal.get("mean_pause_duration_sec", 0.0)),
        "long_pauses": int(temporal.get("long_pauses", 0)),
        "medium_pauses": int(temporal.get("medium_pauses", 0)),
        "short_pauses": int(temporal.get("short_pauses", 0)),
        "pauses": list(temporal.get("pauses", [])),
        "words": normalized,
    }

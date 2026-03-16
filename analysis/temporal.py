"""
Temporal & Fluency Metrics
--------------------------
Processing speed and flow metrics from timestamped words.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from statistics import median


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
        "pause_ratio": (
            round(total_pause / duration_sec, 4) if duration_sec > 0 else 0.0
        ),
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



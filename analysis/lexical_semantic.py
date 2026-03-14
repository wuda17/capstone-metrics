# sentiment analysis
# filler words
# self focus terms

from __future__ import annotations

import re
import string
from typing import Any


FILLER_WORDS = {"um", "uh", "er", "ah", "like", "you know"}
SELF_FOCUS_TERMS = {"i", "me", "my", "mine", "myself"}


def tokenize_text(text: str) -> list[str]:
    clean = text.lower().translate(str.maketrans("", "", string.punctuation))
    return [tok for tok in clean.split() if tok]


def type_token_ratio(text: str) -> float:
    tokens = tokenize_text(text)
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def self_focus_ratio(text: str) -> float:
    tokens = tokenize_text(text)
    if not tokens:
        return 0.0
    self_focus_count = sum(1 for t in tokens if t in SELF_FOCUS_TERMS)
    return self_focus_count / len(tokens)


def filler_word_count(text: str) -> int:
    tokens = tokenize_text(text)
    count = sum(1 for t in tokens if t in FILLER_WORDS)
    count += len(re.findall(r"\byou know\b", text.lower()))
    return count


def sentiment_polarity(text: str) -> float:
    """
    Polarity score in [-1, 1].

    Uses VADER when available; falls back to a tiny lexicon heuristic.
    """
    try:
        from nltk.sentiment import SentimentIntensityAnalyzer

        return float(
            SentimentIntensityAnalyzer().polarity_scores(text).get("compound", 0.0)
        )
    except Exception:
        print("Error calculating sentiment polarity")
        return 0.0


def extract_lexical_semantic_metrics(text: str) -> dict[str, Any]:
    """Aggregate lexical/semantic features into a single payload."""
    return {
        "type_token_ratio": float(type_token_ratio(text)),
        "self_focus_ratio": float(self_focus_ratio(text)),
        "filler_word_count": int(filler_word_count(text)),
        "sentiment_polarity": float(sentiment_polarity(text)),
    }

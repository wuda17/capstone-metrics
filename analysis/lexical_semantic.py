from __future__ import annotations

import logging
import re
from typing import Any

LOGGER = logging.getLogger(__name__)

FILLER_SINGLE_WORDS = {"um", "uh", "er", "ah"}
FILLER_MULTI_WORD_PATTERNS = [
    re.compile(r"\byou know\b", flags=re.IGNORECASE),
    re.compile(r"\bi mean\b", flags=re.IGNORECASE),
    re.compile(r"\bkind of\b", flags=re.IGNORECASE),
    re.compile(r"\bsort of\b", flags=re.IGNORECASE),
]
SELF_FOCUS_TERMS = {
    "i",
    "me",
    "my",
    "mine",
    "myself",
    "i'm",
    "i've",
    "i'll",
    "i'd",
}
TOKEN_PATTERN = re.compile(r"\b[\w']+\b")
LIKELY_FILLER_LIKE_CONTEXT = re.compile(
    r"\blike\b(?=(?:\s+(?:um|uh|you|i|we|so|right))|[,.!?]|$)", flags=re.IGNORECASE
)

_SPACY_TOKENIZER: Any | None = None
_SPACY_UNAVAILABLE = False
_HF_SENTIMENT_PIPELINE: Any | None = None
_HF_EMOTION_PIPELINE: Any | None = None
_HF_PIPELINES_ATTEMPTED = False


def _get_spacy_tokenizer() -> Any | None:
    global _SPACY_TOKENIZER, _SPACY_UNAVAILABLE
    if _SPACY_TOKENIZER is not None or _SPACY_UNAVAILABLE:
        return _SPACY_TOKENIZER
    try:
        import spacy

        _SPACY_TOKENIZER = spacy.blank("en").tokenizer
    except (ImportError, OSError, RuntimeError):
        _SPACY_UNAVAILABLE = True
        _SPACY_TOKENIZER = None
    return _SPACY_TOKENIZER


def _hf_text_classification_pipeline(model_name: str) -> Any | None:
    try:
        from transformers import pipeline

        return pipeline(
            "text-classification",
            model=model_name,
            tokenizer=model_name,
            truncation=True,
            top_k=None,
        )
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        LOGGER.debug("Unable to load classifier model %s: %s", model_name, exc)
        return None


def _get_hf_pipelines() -> tuple[Any | None, Any | None]:
    global _HF_SENTIMENT_PIPELINE, _HF_EMOTION_PIPELINE, _HF_PIPELINES_ATTEMPTED
    if _HF_PIPELINES_ATTEMPTED:
        return _HF_SENTIMENT_PIPELINE, _HF_EMOTION_PIPELINE

    _HF_PIPELINES_ATTEMPTED = True
    _HF_SENTIMENT_PIPELINE = _hf_text_classification_pipeline(
        "cardiffnlp/twitter-roberta-base-sentiment-latest"
    )
    _HF_EMOTION_PIPELINE = _hf_text_classification_pipeline(
        "j-hartmann/emotion-english-distilroberta-base"
    )
    return _HF_SENTIMENT_PIPELINE, _HF_EMOTION_PIPELINE


def tokenize_text(text: str) -> list[str]:
    tokenizer = _get_spacy_tokenizer()
    if tokenizer is not None:
        return [
            tok.text.lower()
            for tok in tokenizer(text)
            if tok.text and not tok.is_space and not tok.is_punct
        ]
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


def type_token_ratio(text: str) -> float:
    tokens = tokenize_text(text)
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def self_pronoun_ratio(text: str) -> float:
    tokens = tokenize_text(text)
    if not tokens:
        return 0.0
    return sum(1 for t in tokens if t in SELF_FOCUS_TERMS) / len(tokens)


def filler_word_count(text: str) -> int:
    tokens = tokenize_text(text)
    count = sum(1 for t in tokens if t in FILLER_SINGLE_WORDS)
    count += sum(len(pattern.findall(text)) for pattern in FILLER_MULTI_WORD_PATTERNS)
    count += len(LIKELY_FILLER_LIKE_CONTEXT.findall(text))
    return count


def sentiment_polarity(text: str) -> float:
    """Polarity score in [-1, 1] from transformer sentiment model."""
    cleaned = text.strip()
    if not cleaned:
        return 0.0
    sentiment_pipeline, _ = _get_hf_pipelines()
    if sentiment_pipeline is None:
        return 0.0
    try:
        raw = sentiment_pipeline(cleaned)
    except (RuntimeError, ValueError, TypeError):
        return 0.0
    predictions = raw[0] if raw and isinstance(raw[0], list) else raw
    label_scores = {
        str(item.get("label", "")).lower(): float(item.get("score", 0.0))
        for item in predictions
        if isinstance(item, dict)
    }
    positive = label_scores.get("positive", 0.0)
    negative = label_scores.get("negative", 0.0)
    return max(-1.0, min(1.0, positive - negative))


def emotion_score(text: str) -> float:
    """Normalized emotion polarity score in [-1, 1]."""
    cleaned = text.strip()
    if not cleaned:
        return 0.0
    _, emotion_pipeline = _get_hf_pipelines()
    if emotion_pipeline is None:
        return sentiment_polarity(cleaned)
    try:
        raw = emotion_pipeline(cleaned)
    except (RuntimeError, ValueError, TypeError):
        return sentiment_polarity(cleaned)
    predictions = raw[0] if raw and isinstance(raw[0], list) else raw
    emotion_valence = {
        "joy": 0.9,
        "surprise": 0.35,
        "neutral": 0.0,
        "sadness": -0.7,
        "anger": -0.9,
        "fear": -0.75,
        "disgust": -0.8,
    }
    weighted_total = 0.0
    total_weight = 0.0
    for item in predictions:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).lower()
        score = float(item.get("score", 0.0))
        weighted_total += emotion_valence.get(label, 0.0) * score
        total_weight += score
    if total_weight <= 0.0:
        return sentiment_polarity(cleaned)
    return max(-1.0, min(1.0, weighted_total / total_weight))


def extract_lexical_semantic_metrics(text: str) -> dict[str, Any]:
    """Aggregate lexical/semantic features into a single payload.

    emotion_score is intentionally excluded here — it is computed once per day
    across all of that day's transcripts by the aggregator service.
    """
    return {
        "type_token_ratio": float(type_token_ratio(text)),
        "self_pronoun_ratio": float(self_pronoun_ratio(text)),
        "filler_word_count": int(filler_word_count(text)),
    }

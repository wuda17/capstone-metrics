"""
Backward-compatible aliases for session metric containers.

Use `analysis.temporal` for new code.
"""

from __future__ import annotations

from .temporal import (
    Pause,
    SessionMetrics,
    UtteranceMetrics,
    Word,
    compute_utterance_metrics,
    words_to_payload,
)

__all__ = [
    "Word",
    "Pause",
    "UtteranceMetrics",
    "SessionMetrics",
    "words_to_payload",
    "compute_utterance_metrics",
]

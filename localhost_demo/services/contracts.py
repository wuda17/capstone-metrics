"""
Shared data contracts for localhost demo services.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import json
import uuid


def now_iso() -> str:
    """Return current UTC timestamp in ISO8601 format."""
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@dataclass
class NewAudioEvent:
    """
    Event emitted when a new WAV file is discovered.
    """

    audio_path: str
    created_at: str
    day: str
    source: str = "watchdog"
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    received_at: str = field(default_factory=now_iso)
    file_size_bytes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SnapshotRecord:
    """
    Persisted metrics snapshot consumed by aggregator/dashboard.
    """

    event: dict[str, Any]
    source_file: str
    transcript: str
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

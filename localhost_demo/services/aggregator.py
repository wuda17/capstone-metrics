#!/usr/bin/env python3
"""
Rolling aggregator service for localhost demo snapshots.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .contracts import append_jsonl, write_json


METRIC_PATHS = {
    "speech_rate_wpm": ("metrics", "temporal", "speech_rate_wpm"),
    "articulation_rate_wpm": ("metrics", "temporal", "articulation_rate_wpm"),
    "phonation_to_time_ratio": ("metrics", "temporal", "phonation_to_time_ratio"),
    "type_token_ratio": ("metrics", "lexical", "type_token_ratio"),
    "mean_pause_duration_sec": ("metrics", "temporal", "mean_pause_duration_sec"),
    "f0_mean_hz": ("metrics", "prosody", "f0_mean_hz"),
    "jitter_local": ("metrics", "prosody", "jitter_local"),
    "shimmer_local_db": ("metrics", "prosody", "shimmer_local_db"),
}


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Aggregate snapshot JSON files")
    parser.add_argument(
        "--snapshots-dir",
        default=str(root / "data" / "snapshots"),
        help="Snapshot JSON input directory",
    )
    parser.add_argument(
        "--current-output",
        default=str(root / "data" / "aggregates" / "current.json"),
        help="Current aggregate JSON path",
    )
    parser.add_argument(
        "--history-output",
        default=str(root / "data" / "aggregates" / "history.jsonl"),
        help="Historical aggregate JSONL path",
    )
    parser.add_argument(
        "--interval-sec",
        type=float,
        default=5.0,
        help="Aggregation refresh interval in seconds",
    )
    parser.add_argument(
        "--max-transcript-items",
        type=int,
        default=20,
        help="Max recent transcript records to include",
    )
    return parser.parse_args()


def _parse_iso(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _read_snapshots(snapshots_dir: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(snapshots_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["_file"] = str(path)
            items.append(payload)
        except (OSError, json.JSONDecodeError):
            continue
    return items


def _extract_metric(snapshot: dict[str, Any], metric_name: str) -> float | None:
    path = METRIC_PATHS[metric_name]
    value: Any = snapshot
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _event_time(snapshot: dict[str, Any]) -> str:
    value = (snapshot.get("event") or {}).get("time")
    return value if isinstance(value, str) else ""


def _snapshot_timestamp(snapshot: dict[str, Any], fallback: datetime) -> datetime:
    try:
        return _parse_iso(_event_time(snapshot))
    except ValueError:
        return fallback


def _snapshot_word_count(snapshot: dict[str, Any]) -> int | None:
    temporal = ((snapshot.get("metrics") or {}).get("temporal") or {})
    if not isinstance(temporal, dict):
        return None
    value = temporal.get("word_count")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _window_metrics(
    snapshots: list[dict[str, Any]],
    now: datetime,
    window_sec: int,
) -> dict[str, float | None]:
    cutoff = now - timedelta(seconds=window_sec)
    recent = [s for s in snapshots if _snapshot_timestamp(s, now) >= cutoff]
    out: dict[str, float | None] = {}
    for metric in METRIC_PATHS:
        vals = [v for v in (_extract_metric(s, metric) for s in recent) if v is not None]
        out[metric] = _mean(vals)
    out["sample_count"] = len(recent)
    return out


def _baseline_metrics(snapshots: list[dict[str, Any]]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for metric in METRIC_PATHS:
        vals = [v for v in (_extract_metric(s, metric) for s in snapshots) if v is not None]
        out[metric] = _mean(vals)
    out["sample_count"] = len(snapshots)
    return out


def _deviation_pct(current: float | None, baseline: float | None) -> float | None:
    if current is None or baseline in (None, 0):
        return None
    return round(((current - baseline) / baseline) * 100.0, 3)


def _latest_transcripts(
    snapshots: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    ordered = sorted(
        snapshots,
        key=_event_time,
        reverse=True,
    )
    recent: list[dict[str, Any]] = []
    for s in ordered[:limit]:
        recent.append(
            {
                "event_time": _event_time(s),
                "day": ((s.get("event") or {}).get("day")),
                "source_file": s.get("source_file"),
                "text": s.get("transcript") if isinstance(s.get("transcript"), str) else "",
                "word_count": _snapshot_word_count(s),
            }
        )
    return recent


def compute_aggregate(
    snapshots: list[dict[str, Any]],
    max_transcript_items: int,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    baseline = _baseline_metrics(snapshots)
    one_min = _window_metrics(snapshots, now, 60)
    five_min = _window_metrics(snapshots, now, 300)

    deviations = {}
    for metric in METRIC_PATHS:
        deviations[metric] = {
            "from_1m_window_pct": _deviation_pct(one_min.get(metric), baseline.get(metric)),
            "from_5m_window_pct": _deviation_pct(five_min.get(metric), baseline.get(metric)),
        }

    return {
        "schema_version": "1.0.0",
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "counts": {"snapshots_total": len(snapshots)},
        "baseline": baseline,
        "windows": {
            "last_60s": one_min,
            "last_300s": five_min,
        },
        "deviations": deviations,
        "latest_transcripts": _latest_transcripts(snapshots, max_transcript_items),
    }


def main() -> None:
    args = parse_args()
    snapshots_dir = Path(args.snapshots_dir)
    current_output = Path(args.current_output)
    history_output = Path(args.history_output)

    snapshots_dir.mkdir(parents=True, exist_ok=True)
    current_output.parent.mkdir(parents=True, exist_ok=True)
    history_output.parent.mkdir(parents=True, exist_ok=True)

    print(f"[Aggregator] Reading snapshots from {snapshots_dir}")
    print(f"[Aggregator] Writing current aggregate to {current_output}")
    print(f"[Aggregator] Appending history to {history_output}")
    print("[Aggregator] Press Ctrl+C to stop")

    try:
        while True:
            snapshots = _read_snapshots(snapshots_dir)
            aggregate = compute_aggregate(
                snapshots,
                args.max_transcript_items,
            )
            write_json(current_output, aggregate)
            append_jsonl(history_output, aggregate)
            time.sleep(args.interval_sec)
    except KeyboardInterrupt:
        print("\n[Aggregator] Stopped")


if __name__ == "__main__":
    main()

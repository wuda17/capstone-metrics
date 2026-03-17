#!/usr/bin/env python3
"""
Rolling aggregator service for localhost demo snapshots.
"""

from __future__ import annotations

import argparse
import json
import math
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
    parser.add_argument(
        "--segment-minutes",
        type=int,
        default=1,
        help="Time-series bucket size in minutes",
    )
    parser.add_argument(
        "--current-window-minutes",
        type=int,
        default=0,
        help="Current window size in minutes for baseline comparison",
    )
    parser.add_argument(
        "--baseline-percent",
        type=float,
        default=0.2,
        help="Earliest snapshot fraction used to compute baseline (0 to 1]",
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


def _metric_means(snapshots: list[dict[str, Any]]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for metric in METRIC_PATHS:
        vals = [v for v in (_extract_metric(s, metric) for s in snapshots) if v is not None]
        out[metric] = _mean(vals)
    return out


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
    out = _metric_means(recent)
    out["sample_count"] = len(recent)
    return out


def _baseline_metrics(snapshots: list[dict[str, Any]]) -> dict[str, float | None]:
    out = _metric_means(snapshots)
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
    now = datetime.now(timezone.utc)
    ordered = sorted(snapshots, key=lambda s: _snapshot_timestamp(s, now), reverse=True)
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


def _ordered_snapshots(snapshots: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    return sorted(snapshots, key=lambda s: _snapshot_timestamp(s, now))


def _floor_to_segment(ts: datetime, segment_minutes: int) -> datetime:
    segment_seconds = max(1, segment_minutes) * 60
    epoch = int(ts.timestamp())
    floored_epoch = (epoch // segment_seconds) * segment_seconds
    return datetime.fromtimestamp(floored_epoch, tz=timezone.utc)


def _time_series(
    snapshots: list[dict[str, Any]],
    now: datetime,
    segment_minutes: int,
) -> list[dict[str, Any]]:
    buckets: dict[datetime, list[dict[str, Any]]] = {}
    segment_delta = timedelta(minutes=max(1, segment_minutes))
    for snapshot in snapshots:
        ts = _snapshot_timestamp(snapshot, now)
        bucket_start = _floor_to_segment(ts, segment_minutes)
        buckets.setdefault(bucket_start, []).append(snapshot)

    rows: list[dict[str, Any]] = []
    for start in sorted(buckets):
        bucket_snapshots = buckets[start]
        rows.append(
            {
                "segment_start": start.isoformat().replace("+00:00", "Z"),
                "segment_end": (start + segment_delta).isoformat().replace("+00:00", "Z"),
                "sample_count": len(bucket_snapshots),
                "values": _metric_means(bucket_snapshots),
            }
        )
    return rows


def _current_metrics(
    snapshots: list[dict[str, Any]],
    now: datetime,
    current_window_minutes: int,
) -> dict[str, Any]:
    cutoff = now - timedelta(minutes=max(1, current_window_minutes))
    recent = [s for s in snapshots if _snapshot_timestamp(s, now) >= cutoff]
    return {
        "window_minutes": max(1, current_window_minutes),
        "sample_count": len(recent),
        "values": _metric_means(recent),
    }


def _baseline_from_earliest_percent(
    snapshots: list[dict[str, Any]],
    now: datetime,
    baseline_percent: float,
) -> dict[str, Any]:
    bounded_percent = min(1.0, max(0.01, baseline_percent))
    ordered = _ordered_snapshots(snapshots, now)
    if not ordered:
        return {
            "method": "earliest_percent",
            "percent": round(bounded_percent, 3),
            "sample_count": 0,
            "values": _metric_means([]),
        }
    count = max(1, math.floor(len(ordered) * bounded_percent))
    cohort = ordered[:count]
    return {
        "method": "earliest_percent",
        "percent": round(bounded_percent, 3),
        "sample_count": len(cohort),
        "values": _metric_means(cohort),
    }


def _metric_trend(delta_abs: float | None) -> str:
    if delta_abs is None:
        return "unknown"
    if delta_abs > 0:
        return "up"
    if delta_abs < 0:
        return "down"
    return "stable"


def _drift_metrics(
    baseline_values: dict[str, float | None],
    current_values: dict[str, float | None],
) -> dict[str, dict[str, float | None | str]]:
    drift: dict[str, dict[str, float | None | str]] = {}
    for metric in METRIC_PATHS:
        baseline = baseline_values.get(metric)
        current = current_values.get(metric)
        delta_abs = (
            round(current - baseline, 6)
            if current is not None and baseline is not None
            else None
        )
        delta_pct = _deviation_pct(current, baseline)
        drift[metric] = {
            "delta_abs": delta_abs,
            "delta_pct": delta_pct,
            "trend": _metric_trend(delta_abs),
        }
    return drift


def _alerts_from_drift(drift: dict[str, dict[str, float | None | str]]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for metric, item in drift.items():
        delta_pct = item.get("delta_pct")
        if not isinstance(delta_pct, (float, int)):
            continue
        magnitude = abs(float(delta_pct))
        if magnitude < 20.0:
            continue
        severity = "high" if magnitude >= 40.0 else "medium"
        alerts.append(
            {
                "status": "alert",
                "severity": severity,
                "metric": metric,
                "delta_pct": round(float(delta_pct), 3),
                "trend": item.get("trend"),
                "message": (
                    f"{metric} is {magnitude:.1f}% "
                    f"{'above' if delta_pct > 0 else 'below'} baseline."
                ),
            }
        )
    alerts.sort(key=lambda a: abs(float(a["delta_pct"])), reverse=True)
    if alerts:
        return alerts
    return [
        {
            "status": "ok",
            "severity": "none",
            "metric": None,
            "delta_pct": None,
            "trend": "stable",
            "message": "All tracked metrics are within baseline tolerance.",
        }
    ]


def compute_aggregate(
    snapshots: list[dict[str, Any]],
    max_transcript_items: int,
    segment_minutes: int,
    current_window_minutes: int,
    baseline_percent: float,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    time_series = _time_series(snapshots, now, segment_minutes)
    baseline_obj = _baseline_from_earliest_percent(snapshots, now, baseline_percent)
    current_obj = _current_metrics(snapshots, now, current_window_minutes)
    drift = _drift_metrics(
        baseline_obj["values"],
        current_obj["values"],
    )
    alerts = _alerts_from_drift(drift)

    baseline = dict(baseline_obj["values"])
    baseline["sample_count"] = baseline_obj["sample_count"]

    one_min = _window_metrics(snapshots, now, 60)
    five_min = _window_metrics(snapshots, now, 300)

    deviations = {}
    for metric in METRIC_PATHS:
        deviations[metric] = {
            "from_current_window_pct": _deviation_pct(
                current_obj["values"].get(metric),
                baseline.get(metric),
            ),
            "from_1m_window_pct": _deviation_pct(one_min.get(metric), baseline.get(metric)),
            "from_5m_window_pct": _deviation_pct(five_min.get(metric), baseline.get(metric)),
        }

    transcripts = _latest_transcripts(snapshots, max_transcript_items)

    return {
        "meta": {
            "schema_version": "2.0.0",
            "generated_at": now.isoformat().replace("+00:00", "Z"),
            "segment_minutes": max(1, segment_minutes),
            "snapshot_count": len(snapshots),
        },
        "metrics": {
            "time_series": time_series,
            "baseline": baseline_obj,
            "current": current_obj,
        },
        "transcripts": {
            "items": transcripts,
        },
        "alerts": {
            "items": alerts,
            "deviations": deviations,
        },
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
                args.segment_minutes,
                args.current_window_minutes if args.current_window_minutes > 0 else args.segment_minutes,
                args.baseline_percent,
            )
            write_json(current_output, aggregate)
            append_jsonl(history_output, aggregate)
            time.sleep(args.interval_sec)
    except KeyboardInterrupt:
        print("\n[Aggregator] Stopped")


if __name__ == "__main__":
    main()

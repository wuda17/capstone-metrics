#!/usr/bin/env python3
"""
Rolling aggregator service for localhost demo snapshots.
"""

from __future__ import annotations

import argparse
import json
import math
import string
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .contracts import append_jsonl, write_json


METRIC_PATHS = {
    "speech_rate_wpm": ("metrics", "temporal", "speech_rate_wpm"),
    "articulation_rate_wpm": ("metrics", "temporal", "articulation_rate_wpm"),
    "phonation_to_time_ratio": ("metrics", "temporal", "phonation_to_time_ratio"),
    "mean_pause_duration_sec": ("metrics", "temporal", "mean_pause_duration_sec"),
    "f0_mean_hz": ("metrics", "prosody", "f0_mean_hz"),
    "jitter_local": ("metrics", "prosody", "jitter_local"),
    "shimmer_local_db": ("metrics", "prosody", "shimmer_local_db"),
}

LEXICAL_METRIC_NAMES = (
    "emotion_score",
    "self_pronoun_ratio",
    "type_token_ratio",
)

TRACKED_METRICS = tuple(METRIC_PATHS.keys()) + LEXICAL_METRIC_NAMES
SELF_PRONOUN_TERMS = {"i", "me", "my", "mine", "myself"}

# Human-readable display names for each tracked metric
METRIC_LABELS: dict[str, str] = {
    "speech_rate_wpm":         "Speaking Speed",
    "articulation_rate_wpm":   "Articulation Rate",
    "phonation_to_time_ratio": "Phonation Ratio",
    "mean_pause_duration_sec": "Mean Pause Duration",
    "f0_mean_hz":              "Pitch (F0)",
    "jitter_local":            "Voice Jitter",
    "shimmer_local_db":        "Voice Shimmer",
    "type_token_ratio":        "Vocabulary Diversity",
    "emotion_score":           "Mood Score",
    "self_pronoun_ratio":      "Self-Reference",
}

# Minimum snapshots required before baseline comparisons are meaningful
MIN_SNAPSHOTS_FOR_ALERTS = 5


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
    parser.add_argument(
        "--daily-cache",
        default=str(root / "data" / "daily_lexical.json"),
        help="Path to daily emotion-score cache JSON",
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


def _metric_means(
    snapshots: list[dict[str, Any]],
    daily_emotion_cache: dict[str, Any] | None = None,
) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for metric in METRIC_PATHS:
        vals = [v for v in (_extract_metric(s, metric) for s in snapshots) if v is not None]
        out[metric] = _mean(vals)
    out.update(_conversation_lexical_metrics(snapshots, daily_emotion_cache))
    return out


def _load_daily_cache(cache_path: Path) -> dict[str, Any]:
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_daily_cache(cache_path: Path, cache: dict[str, Any]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


def _refresh_daily_emotion(
    snapshots: list[dict[str, Any]],
    cache_path: Path,
) -> dict[str, Any]:
    """Recompute HuggingFace emotion_score for any day whose snapshot count changed.

    Groups snapshots by day, concatenates their transcripts, runs the
    analysis.lexical_semantic.emotion_score model, and persists the result.
    Returns the updated cache dict so compute_aggregate can inject the values.
    """
    cache = _load_daily_cache(cache_path)

    by_day: dict[str, list[dict[str, Any]]] = {}
    for snapshot in snapshots:
        day = (snapshot.get("event") or {}).get("day", "")
        if day:
            by_day.setdefault(day, []).append(snapshot)

    updated = False
    for day, day_snaps in by_day.items():
        count = len(day_snaps)
        if (cache.get(day) or {}).get("snapshot_count") == count:
            continue
        texts = [
            s.get("transcript", "")
            for s in day_snaps
            if isinstance(s.get("transcript"), str)
        ]
        corpus = " ".join(t for t in texts if t.strip())
        try:
            from analysis.lexical_semantic import emotion_score as _hf_emotion
            score = float(_hf_emotion(corpus)) if corpus else 0.0
        except Exception:
            score = 0.0
        cache[day] = {"emotion_score": round(score, 6), "snapshot_count": count}
        updated = True

    if updated:
        _save_daily_cache(cache_path, cache)
    return cache


def _tokenize_text(text: str) -> list[str]:
    clean = text.lower().translate(str.maketrans("", "", string.punctuation))
    return [tok for tok in clean.split() if tok]


def _type_token_ratio(text: str) -> float | None:
    tokens = _tokenize_text(text)
    if not tokens:
        return None
    return len(set(tokens)) / len(tokens)


def _self_pronoun_ratio(text: str) -> float | None:
    tokens = _tokenize_text(text)
    if not tokens:
        return None
    count = sum(1 for token in tokens if token in SELF_PRONOUN_TERMS)
    return count / len(tokens)


def _conversation_lexical_metrics(
    snapshots: list[dict[str, Any]],
    daily_emotion_cache: dict[str, Any] | None = None,
) -> dict[str, float]:
    now = datetime.now(timezone.utc)
    ordered = _ordered_snapshots(snapshots, now)
    corpus_parts: list[str] = []
    for item in ordered:
        text = item.get("transcript")
        if isinstance(text, str) and text.strip():
            corpus_parts.append(text)
    corpus = " ".join(corpus_parts)

    # emotion_score: average the cached daily values for the days covered by
    # these snapshots.  Falls back to 0.0 when no cache entry is available.
    if daily_emotion_cache:
        days = {
            (s.get("event") or {}).get("day", "")
            for s in snapshots
            if (s.get("event") or {}).get("day")
        }
        day_scores = [
            float(daily_emotion_cache[d]["emotion_score"])
            for d in days
            if d in daily_emotion_cache
            and isinstance((daily_emotion_cache[d] or {}).get("emotion_score"), (int, float))
        ]
        emo: float | None = sum(day_scores) / len(day_scores) if day_scores else None
    else:
        emo = None

    ttr = _type_token_ratio(corpus)
    spr = _self_pronoun_ratio(corpus)

    return {
        "emotion_score": round(float(emo), 6) if emo is not None else None,
        "self_pronoun_ratio": float(spr) if spr is not None else None,
        "type_token_ratio": float(ttr) if ttr is not None else None,
    }


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
    daily_emotion_cache: dict[str, Any] | None = None,
) -> dict[str, float | None]:
    cutoff = now - timedelta(seconds=window_sec)
    recent = [s for s in snapshots if _snapshot_timestamp(s, now) >= cutoff]
    out = _metric_means(recent, daily_emotion_cache)
    out["sample_count"] = len(recent)
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
    daily_emotion_cache: dict[str, Any] | None = None,
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
                "values": _metric_means(bucket_snapshots, daily_emotion_cache),
            }
        )
    return rows


def _current_metrics(
    snapshots: list[dict[str, Any]],
    now: datetime,
    current_window_minutes: int,
    daily_emotion_cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cutoff = now - timedelta(minutes=max(1, current_window_minutes))
    recent = [s for s in snapshots if _snapshot_timestamp(s, now) >= cutoff]
    return {
        "window_minutes": max(1, current_window_minutes),
        "sample_count": len(recent),
        "values": _metric_means(recent, daily_emotion_cache),
    }


def _baseline_from_earliest_percent(
    snapshots: list[dict[str, Any]],
    now: datetime,
    baseline_percent: float,
    daily_emotion_cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bounded_percent = min(1.0, max(0.01, baseline_percent))
    ordered = _ordered_snapshots(snapshots, now)
    if not ordered:
        return {
            "method": "earliest_percent",
            "percent": round(bounded_percent, 3),
            "sample_count": 0,
            "values": _metric_means([], daily_emotion_cache),
        }
    count = max(1, math.floor(len(ordered) * bounded_percent))
    cohort = ordered[:count]
    return {
        "method": "earliest_percent",
        "percent": round(bounded_percent, 3),
        "sample_count": len(cohort),
        "values": _metric_means(cohort, daily_emotion_cache),
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
    for metric in TRACKED_METRICS:
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
        display_name = METRIC_LABELS.get(metric, metric.replace("_", " ").title())
        alerts.append(
            {
                "status": "alert",
                "severity": severity,
                "metric": metric,
                "label": display_name,
                "delta_pct": round(float(delta_pct), 3),
                "trend": item.get("trend"),
                "message": (
                    f"{display_name} is {magnitude:.1f}% "
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
    daily_emotion_cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    time_series = _time_series(snapshots, now, segment_minutes, daily_emotion_cache)
    baseline_obj = _baseline_from_earliest_percent(snapshots, now, baseline_percent, daily_emotion_cache)
    current_obj = _current_metrics(snapshots, now, current_window_minutes, daily_emotion_cache)
    # For alert comparison, fall back to the latest time-series bucket values
    # when the current window has no data (None) for a metric.  This prevents
    # false alerts when the rolling window contains no transcript text (lexical
    # metrics now return None on an empty corpus instead of 0.0).
    ts_latest_values = time_series[-1]["values"] if time_series else {}
    comparison_values: dict[str, float | None] = {
        metric: (
            current_obj["values"].get(metric)
            if current_obj["values"].get(metric) is not None
            else ts_latest_values.get(metric)
        )
        for metric in TRACKED_METRICS
    }

    drift = _drift_metrics(
        baseline_obj["values"],
        comparison_values,
    )
    if len(snapshots) >= MIN_SNAPSHOTS_FOR_ALERTS:
        alerts = _alerts_from_drift(drift)
    else:
        alerts = [
            {
                "status": "ok",
                "severity": "none",
                "metric": None,
                "label": None,
                "delta_pct": None,
                "trend": "stable",
                "message": (
                    f"Collecting baseline data — alerts will activate after "
                    f"{MIN_SNAPSHOTS_FOR_ALERTS} sessions are recorded "
                    f"({len(snapshots)} so far)."
                ),
            }
        ]

    baseline = dict(baseline_obj["values"])
    baseline["sample_count"] = baseline_obj["sample_count"]

    one_min = _window_metrics(snapshots, now, 60, daily_emotion_cache)
    five_min = _window_metrics(snapshots, now, 300, daily_emotion_cache)

    deviations = {}
    for metric in TRACKED_METRICS:
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
    daily_cache_path = Path(args.daily_cache)

    snapshots_dir.mkdir(parents=True, exist_ok=True)
    current_output.parent.mkdir(parents=True, exist_ok=True)
    history_output.parent.mkdir(parents=True, exist_ok=True)

    print(f"[Aggregator] Reading snapshots from {snapshots_dir}")
    print(f"[Aggregator] Writing current aggregate to {current_output}")
    print(f"[Aggregator] Appending history to {history_output}")
    print(f"[Aggregator] Daily emotion cache: {daily_cache_path}")
    print("[Aggregator] Press Ctrl+C to stop")

    try:
        while True:
            snapshots = _read_snapshots(snapshots_dir)
            daily_emotion = _refresh_daily_emotion(snapshots, daily_cache_path)
            aggregate = compute_aggregate(
                snapshots,
                args.max_transcript_items,
                args.segment_minutes,
                args.current_window_minutes if args.current_window_minutes > 0 else args.segment_minutes,
                args.baseline_percent,
                daily_emotion_cache=daily_emotion,
            )
            write_json(current_output, aggregate)
            append_jsonl(history_output, aggregate)
            time.sleep(args.interval_sec)
    except KeyboardInterrupt:
        print("\n[Aggregator] Stopped")


if __name__ == "__main__":
    main()

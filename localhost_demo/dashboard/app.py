#!/usr/bin/env python3
"""Minimal clinical insights dashboard for FERBAI."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AGGREGATE = ROOT / "data" / "aggregates" / "current.json"
DEFAULT_SNAPSHOTS = ROOT / "data" / "snapshots"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def load_snapshots(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for file in sorted(path.glob("*.json")):
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
            rows.append(payload)
        except (OSError, json.JSONDecodeError):
            continue
    return rows


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_window_metric(aggregate: dict[str, Any], metric_name: str) -> float | None:
    windows = aggregate.get("windows", {})
    value = (windows.get("last_60s") or {}).get(metric_name)
    return _to_float(value)


def _get_baseline_metric(aggregate: dict[str, Any], metric_name: str) -> float | None:
    value = (aggregate.get("baseline") or {}).get(metric_name)
    return _to_float(value)


def _deviation_pct(aggregate: dict[str, Any], metric_name: str) -> float | None:
    metric = (aggregate.get("deviations") or {}).get(metric_name) or {}
    pct = metric.get("from_1m_window_pct")
    if pct is None:
        pct = metric.get("from_5m_window_pct")
    return _to_float(pct)


def make_timeseries_df(snapshots: list[dict[str, Any]]) -> pd.DataFrame:
    items = []
    for s in snapshots:
        metrics = s.get("metrics", {})
        temporal = metrics.get("temporal", {}) if isinstance(metrics, dict) else {}
        lexical = metrics.get("lexical", {}) if isinstance(metrics, dict) else {}
        prosody = metrics.get("prosody", {}) if isinstance(metrics, dict) else {}
        event = s.get("event", {}) if isinstance(s.get("event"), dict) else {}
        items.append(
            {
                "processed_at": event.get("time"),
                "speech_rate_wpm": temporal.get("speech_rate_wpm"),
                "articulation_rate_wpm": temporal.get("articulation_rate_wpm"),
                "phonation_to_time_ratio": temporal.get("phonation_to_time_ratio"),
                "type_token_ratio": lexical.get("type_token_ratio"),
                "mean_pause_duration_sec": temporal.get("mean_pause_duration_sec"),
                "f0_mean_hz": prosody.get("f0_mean_hz"),
                "jitter_local": prosody.get("jitter_local"),
            }
        )
    if not items:
        return pd.DataFrame()
    df = pd.DataFrame(items)
    df["processed_at"] = pd.to_datetime(df["processed_at"], errors="coerce")
    df = df.dropna(subset=["processed_at"]).sort_values("processed_at")
    return df


def _acuity_score(aggregate: dict[str, Any]) -> tuple[int, str, str]:
    score = 100.0
    tracked_metrics = ("mean_pause_duration_sec", "type_token_ratio")
    for metric in tracked_metrics:
        pct = _deviation_pct(aggregate, metric)
        if pct is None:
            continue
        magnitude = abs(pct)
        if magnitude > 20.0:
            score -= 25.0
            if magnitude > 40.0:
                score -= 10.0
    score = max(0.0, min(100.0, score))
    rounded = int(round(score))
    if rounded >= 80:
        return rounded, "Green", "#16A34A"
    if rounded >= 60:
        return rounded, "Yellow", "#D97706"
    return rounded, "Red", "#DC2626"


def _status_dot_html(label: str, color_hex: str) -> str:
    return (
        f"<span style='font-size:1.1rem;'>"
        f"<span style='color:{color_hex};'>●</span> "
        f"{label}"
        f"</span>"
    )


def _simple_comparison_df(
    current: float | None,
    baseline: float | None,
    current_label: str,
    baseline_label: str,
) -> pd.DataFrame:
    data = []
    if baseline is not None:
        data.append({"Window": baseline_label, "Value": baseline})
    if current is not None:
        data.append({"Window": current_label, "Value": current})
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data).set_index("Window")


def _trend_with_baseline(
    timeseries: pd.DataFrame,
    metric_name: str,
    chart_label: str,
    baseline: float | None,
) -> pd.DataFrame:
    if timeseries.empty or metric_name not in timeseries.columns:
        return pd.DataFrame()
    df = timeseries[["processed_at", metric_name]].copy()
    df = df.dropna(subset=[metric_name]).tail(20)
    if df.empty:
        return pd.DataFrame()
    df = df.rename(columns={metric_name: chart_label}).set_index("processed_at")
    if baseline is not None:
        df["Baseline"] = baseline
    return df


def _latest_transcript(aggregate: dict[str, Any]) -> str:
    direct = aggregate.get("latest_transcript")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    latest_items = aggregate.get("latest_transcripts", [])
    if not latest_items:
        return "No transcript yet."
    text = (latest_items[0] or {}).get("text", "")
    return text.strip() or "No transcript yet."


def _metadata_word_count(aggregate: dict[str, Any]) -> int:
    value = aggregate.get("word_count")
    if isinstance(value, int):
        return value
    items = aggregate.get("latest_transcripts", [])
    return int(sum((item or {}).get("word_count", 0) or 0 for item in items))


def _metadata_vocal_minutes(aggregate: dict[str, Any]) -> float:
    value = aggregate.get("vocal_minutes")
    if value is not None:
        parsed = _to_float(value)
        if parsed is not None:
            return parsed
    ratio = _get_baseline_metric(aggregate, "phonation_to_time_ratio")
    if ratio is None:
        return 0.0
    return round(ratio * 5.0, 2)


def main() -> None:
    st.set_page_config(page_title="FERBAI Clinical Insights", layout="wide")
    st.title("FERBAI Clinical Insights")
    st.caption("Minimal caregiver-facing view with high-level status and trend signals.")

    aggregate_path = Path(
        st.sidebar.text_input("Aggregate JSON path", str(DEFAULT_AGGREGATE))
    )
    snapshot_path = Path(
        st.sidebar.text_input("Snapshots directory", str(DEFAULT_SNAPSHOTS))
    )
    auto_refresh = st.sidebar.toggle("Auto refresh", value=True)
    refresh_sec = st.sidebar.slider("Refresh interval (sec)", 2, 30, 5)

    aggregate = load_json(aggregate_path)
    snapshots = load_snapshots(snapshot_path)
    timeseries = make_timeseries_df(snapshots)
    if not aggregate:
        st.info("Waiting for aggregate output JSON.")
        if auto_refresh:
            time.sleep(refresh_sec)
            st.rerun()
        return

    acuity, acuity_label, acuity_color = _acuity_score(aggregate)
    left, right = st.columns([2, 1])
    with left:
        st.metric("Acuity Score", f"{acuity}/100")
        st.markdown(
            _status_dot_html(f"Status: {acuity_label}", acuity_color),
            unsafe_allow_html=True,
        )
    with right:
        st.caption("Latest transcript")
        st.write(_latest_transcript(aggregate))
        m1, m2 = st.columns(2)
        m1.metric("Word Count", _metadata_word_count(aggregate))
        m2.metric("Vocal Minutes", f"{_metadata_vocal_minutes(aggregate):.2f}")

    st.markdown("---")
    st.subheader("Big 3 Clinical Trends")

    # 1) Fluency Trend
    st.markdown("**Speaking Speed**")
    speed_df = _trend_with_baseline(
        timeseries,
        metric_name="speech_rate_wpm",
        chart_label="Speaking Speed",
        baseline=_get_baseline_metric(aggregate, "speech_rate_wpm"),
    )
    if speed_df.empty:
        speed_df = _simple_comparison_df(
            current=_get_window_metric(aggregate, "speech_rate_wpm"),
            baseline=_get_baseline_metric(aggregate, "speech_rate_wpm"),
            current_label="Last 60s",
            baseline_label="Baseline",
        )
    if speed_df.empty:
        st.info("Speaking speed data not available yet.")
    else:
        st.line_chart(speed_df)

    # 2) Cognitive Effort Trend
    st.markdown("**Pause Length (Cognitive Load)**")
    pause_df = _trend_with_baseline(
        timeseries,
        metric_name="mean_pause_duration_sec",
        chart_label="Pause Length (Cognitive Load)",
        baseline=_get_baseline_metric(aggregate, "mean_pause_duration_sec"),
    )
    if pause_df.empty:
        pause_df = _simple_comparison_df(
            current=_get_window_metric(aggregate, "mean_pause_duration_sec"),
            baseline=_get_baseline_metric(aggregate, "mean_pause_duration_sec"),
            current_label="Last 60s",
            baseline_label="Baseline",
        )
    if pause_df.empty:
        st.info("Pause length data not available yet.")
    else:
        st.line_chart(pause_df)

    # 3) Vocal Quality Trend
    st.markdown("**Voice Stability (Physical Health)**")
    jitter_df = _trend_with_baseline(
        timeseries,
        metric_name="jitter_local",
        chart_label="Voice Stability (Physical Health)",
        baseline=_get_baseline_metric(aggregate, "jitter_local"),
    )
    if jitter_df.empty:
        jitter_df = _simple_comparison_df(
            current=_get_window_metric(aggregate, "jitter_local"),
            baseline=_get_baseline_metric(aggregate, "jitter_local"),
            current_label="Last 60s",
            baseline_label="Baseline",
        )
    if jitter_df.empty:
        st.info("Voice stability data not available yet.")
    else:
        st.line_chart(jitter_df)

    if auto_refresh:
        time.sleep(refresh_sec)
        st.rerun()


if __name__ == "__main__":
    main()

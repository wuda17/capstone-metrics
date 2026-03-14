#!/usr/bin/env python3
"""
Streamlit dashboard for localhost speech-health demo.
"""

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


def make_timeseries_df(snapshots: list[dict[str, Any]]) -> pd.DataFrame:
    items = []
    for s in snapshots:
        metrics = s.get("metrics", {})
        acoustic = s.get("acoustic", {})
        items.append(
            {
                "processed_at": s.get("processed_at"),
                "speech_rate_wpm": metrics.get("speech_rate_wpm"),
                "articulation_rate_wpm": metrics.get("articulation_rate_wpm"),
                "phonation_to_time_ratio": metrics.get("phonation_to_time_ratio"),
                "type_token_ratio": metrics.get("type_token_ratio"),
                "mean_pause_duration_sec": metrics.get("mean_pause_duration_sec"),
                "f0_mean_hz": acoustic.get("f0_mean_hz"),
            }
        )
    if not items:
        return pd.DataFrame()
    df = pd.DataFrame(items)
    df["processed_at"] = pd.to_datetime(df["processed_at"], errors="coerce")
    df = df.dropna(subset=["processed_at"]).sort_values("processed_at")
    return df


def render_kpis(aggregate: dict[str, Any]) -> None:
    windows = aggregate.get("windows", {})
    last_60s = windows.get("last_60s", {})
    dev = aggregate.get("deviations", {})

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric(
        "F0 mean (1m)",
        _fmt(last_60s.get("f0_mean_hz")),
        _fmt_delta(dev, "f0_mean_hz"),
    )
    c2.metric(
        "Pause duration (1m)",
        _fmt(last_60s.get("mean_pause_duration_sec")),
        _fmt_delta(dev, "mean_pause_duration_sec"),
    )
    c3.metric(
        "Speech rate (1m)",
        _fmt(last_60s.get("speech_rate_wpm")),
        _fmt_delta(dev, "speech_rate_wpm"),
    )
    c4.metric(
        "TTR (1m)",
        _fmt(last_60s.get("type_token_ratio")),
        _fmt_delta(dev, "type_token_ratio"),
    )
    c5.metric(
        "Articulation (1m)",
        _fmt(last_60s.get("articulation_rate_wpm")),
        _fmt_delta(dev, "articulation_rate_wpm"),
    )
    c6.metric(
        "Phonation ratio (1m)",
        _fmt(last_60s.get("phonation_to_time_ratio")),
        _fmt_delta(dev, "phonation_to_time_ratio"),
    )


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "n/a"


def _fmt_delta(deviations: dict[str, Any], metric_name: str) -> str:
    metric = deviations.get(metric_name, {})
    pct = metric.get("from_1m_window_pct")
    if pct is None:
        return "n/a"
    try:
        return f"{float(pct):+.2f}% vs baseline"
    except (TypeError, ValueError):
        return "n/a"


def render_transcript_log(aggregate: dict[str, Any]) -> None:
    items = aggregate.get("latest_transcripts", [])
    st.subheader("Conversation Log")
    if not items:
        st.info("No transcript entries yet.")
        return
    for item in items:
        text = item.get("text", "").strip() or "[empty transcript]"
        ts = item.get("processed_at", "unknown time")
        src = item.get("source_file", "unknown file")
        wc = item.get("word_count", 0)
        st.markdown(f"- `{ts}` • `{src}` • {wc} words\n\n  {text}")


def main() -> None:
    st.set_page_config(page_title="Localhost Speech Health Demo", layout="wide")
    st.title("Localhost Speech Health Demo")
    st.caption("Watchdog -> Metrics -> Aggregator -> Dashboard")

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

    left, right = st.columns([2, 1])
    with left:
        st.subheader("Live Trend Metrics")
        if timeseries.empty:
            st.info("No snapshots available yet.")
        else:
            chart_df = timeseries.set_index("processed_at")[
                [
                    "f0_mean_hz",
                    "mean_pause_duration_sec",
                    "speech_rate_wpm",
                    "articulation_rate_wpm",
                    "phonation_to_time_ratio",
                    "type_token_ratio",
                ]
            ]
            st.line_chart(chart_df)

    with right:
        st.subheader("Baseline Deviations")
        if not aggregate:
            st.info("No aggregate output yet.")
        else:
            render_kpis(aggregate)
            st.markdown("---")
            st.write("Generated at:", aggregate.get("generated_at", "n/a"))
            st.write("Snapshots:", aggregate.get("counts", {}).get("snapshots_total", 0))

    render_transcript_log(aggregate)

    if auto_refresh:
        time.sleep(refresh_sec)
        st.rerun()


if __name__ == "__main__":
    main()

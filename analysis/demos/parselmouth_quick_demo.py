#!/usr/bin/env python3
"""
Quick Parselmouth feature inspection demo.

Usage:
  python analysis/demos/parselmouth_quick_demo.py --audio path/to/file.wav
  python analysis/demos/parselmouth_quick_demo.py --audio path/to/file.wav --raw
  python analysis/demos/parselmouth_quick_demo.py --audio path/to/file.wav --json out.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

# Allow running this file directly with "python analysis/demos/..."
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analysis.audio_utils import temporary_standardized_wav
from analysis.prosody_voice import extract_prosody_voice_metrics


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        out = float(value)
        if out != out or out in (float("inf"), float("-inf")):
            return None
        return out
    except (TypeError, ValueError):
        return None


def extract_raw_parselmouth_stats(audio_path: str | Path) -> dict[str, Any]:
    """Direct Parselmouth/Praat calls for quick low-level inspection."""
    try:
        import parselmouth
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing dependency 'praat-parselmouth'.") from exc

    with temporary_standardized_wav(audio_path) as std_path:  # pylint: disable=not-context-manager
        snd = parselmouth.Sound(str(std_path))
        duration = _to_float(snd.get_total_duration())

        pitch = snd.to_pitch()
        harmonicity = snd.to_harmonicity_cc()
        intensity = snd.to_intensity()
        point_process = parselmouth.praat.call(
            snd, "To PointProcess (periodic, cc)", 75, 500
        )

        return {
            "duration_sec": duration,
            "f0_mean_hz": _to_float(
                parselmouth.praat.call(pitch, "Get mean", 0, 0, "Hertz")
            ),
            "f0_min_hz": _to_float(
                parselmouth.praat.call(
                    pitch, "Get minimum", 0, 0, "Hertz", "Parabolic"
                )
            ),
            "f0_max_hz": _to_float(
                parselmouth.praat.call(
                    pitch, "Get maximum", 0, 0, "Hertz", "Parabolic"
                )
            ),
            "f0_stdev_hz": _to_float(
                parselmouth.praat.call(
                    pitch, "Get standard deviation", 0, 0, "Hertz"
                )
            ),
            "hnr_db": _to_float(parselmouth.praat.call(harmonicity, "Get mean", 0, 0)),
            "intensity_mean_db": _to_float(
                parselmouth.praat.call(intensity, "Get mean", 0, 0, "energy")
            ),
            "jitter_local": _to_float(
                parselmouth.praat.call(
                    point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3
                )
            ),
            "shimmer_local_db": _to_float(
                parselmouth.praat.call(
                    [snd, point_process],
                    "Get shimmer (local_dB)",
                    0,
                    0,
                    0.0001,
                    0.02,
                    1.3,
                    1.6,
                )
            ),
        }


def _print_feature_block(title: str, features: dict[str, Any]) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    for key in sorted(features.keys()):
        value = features[key]
        if isinstance(value, float):
            print(f"{key:24s}: {value:.6f}")
        else:
            print(f"{key:24s}: {value}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect Parselmouth-derived speech features for one audio file."
    )
    parser.add_argument(
        "--audio",
        required=True,
        help="Path to input audio file (wav recommended).",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Also print direct low-level Parselmouth stats.",
    )
    parser.add_argument(
        "--json",
        default="",
        help="Optional JSON output path.",
    )
    args = parser.parse_args()

    audio_path = Path(args.audio)
    if not audio_path.exists():
        raise SystemExit(f"Audio file not found: {audio_path}")

    normalized = extract_prosody_voice_metrics(audio_path)
    _print_feature_block("Normalized Prosody Features", normalized)

    payload: dict[str, Any] = {"normalized_prosody": normalized}
    if args.raw:
        raw = extract_raw_parselmouth_stats(audio_path)
        _print_feature_block("Raw Parselmouth Stats", raw)
        payload["raw_parselmouth"] = raw

    if args.json:
        out_path = Path(args.json)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nSaved JSON to: {out_path}")


if __name__ == "__main__":
    main()

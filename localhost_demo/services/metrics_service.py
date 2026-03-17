#!/usr/bin/env python3
"""
Watchdog-driven metrics service for localhost demo.

Flow:
1) Watch incoming directory for new .wav files
2) Emit normalized new-audio events
3) Run calculator pipeline (transcript + linguistic + acoustic + custom)
4) Persist snapshot JSON with calculator outputs
5) Delete source audio after successful extraction (privacy guardrail)
"""

from __future__ import annotations

import argparse
import os
import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from analysis.interfaces import AnalysisBackend
from analysis.pipeline import build_default_analysis_backend

from .contracts import NewAudioEvent, SnapshotRecord, append_jsonl, write_json


SUPPORTED_EXT = {".wav"}


@dataclass
class PipelineContext:
    """Context shared across processing pipeline phases and calculators."""

    event: NewAudioEvent
    audio_path: Path
    audio: Any
    sample_rate: int
    validation: dict[str, Any]
    transcription: dict[str, Any]


class NewAudioHandler:
    """Watchdog handler that converts filesystem events into audio events."""

    def __init__(self, processor: "MetricsProcessor"):
        self.processor = processor

    def on_created(self, event: Any) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in SUPPORTED_EXT:
            return
        self.processor.enqueue_audio(path, source="watchdog")


class MetricsProcessor:
    """
    Consumes audio events and writes snapshot JSON records.

    The processor depends only on the `AnalysisBackend` interface from
    `analysis.pipeline`, so analysis internals remain swappable.
    """

    def __init__(
        self,
        snapshots_dir: Path,
        events_log: Path,
        whisper_model: str,
        delete_source: bool = True,
        analysis_backend: AnalysisBackend | None = None,
    ):
        self.snapshots_dir = snapshots_dir
        self.events_log = events_log
        self.delete_source = delete_source
        self.queue: queue.Queue[NewAudioEvent] = queue.Queue()
        self.stop_event = threading.Event()

        self.analysis_backend = analysis_backend or build_default_analysis_backend(
            whisper_model=whisper_model
        )

    def enqueue_audio(self, audio_path: Path, source: str) -> None:
        # Wait for file writes to settle before any heavy processing.
        if not self._wait_for_stable_file(audio_path):
            print(f"[MetricsService] Skipping unstable file: {audio_path}")
            return

        stat = audio_path.stat()
        created_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
        event = NewAudioEvent(
            audio_path=str(audio_path.resolve()),
            created_at=created_at,
            day=created_at[:10],
            source=source,
            file_size_bytes=stat.st_size,
        )
        self.queue.put(event)
        append_jsonl(self.events_log, event.to_dict())
        print(f"[MetricsService] Enqueued {audio_path.name} ({event.event_id})")

    def run_worker_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                event = self.queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                self._process_event(event)
            except Exception as exc:  # defensive logging for long-running service
                print(
                    f"[MetricsService] Failed to process event {event.event_id}: {exc}"
                )
            finally:
                self.queue.task_done()

    def _process_event(self, event: NewAudioEvent) -> None:
        audio_path = Path(event.audio_path)
        if not audio_path.exists():
            print(f"[MetricsService] Source vanished before processing: {audio_path}")
            return

        context = self._build_context(event, audio_path)
        if context is None:
            return

        calculator_outputs = self._run_calculators(context)
        snapshot = self._build_snapshot(context, calculator_outputs)
        output_path = self._persist_snapshot(audio_path, snapshot)
        print(f"[MetricsService] Snapshot written: {output_path.name}")

        if self.delete_source:
            try:
                os.unlink(audio_path)
                print(f"[MetricsService] Deleted source audio: {audio_path.name}")
            except OSError as exc:
                print(f"[MetricsService] Warning: could not delete {audio_path}: {exc}")

    def _build_context(
        self, event: NewAudioEvent, audio_path: Path
    ) -> PipelineContext | None:
        audio, sample_rate = self.analysis_backend.prepare_audio(audio_path)
        validation = self.analysis_backend.validate_prepared_audio(audio, sample_rate)
        if not validation["valid"]:
            print(
                f"[MetricsService] Invalid audio {audio_path.name}: {validation['errors']}"
            )
            return None

        transcription = self.analysis_backend.transcribe_audio(
            audio_path, speaker="user"
        )
        return PipelineContext(
            event=event,
            audio_path=audio_path,
            audio=audio,
            sample_rate=sample_rate,
            validation=validation,
            transcription=transcription,
        )

    def _run_calculators(self, context: PipelineContext) -> dict[str, dict[str, Any]]:
        try:
            return self.analysis_backend.calculate(
                audio_path=context.audio_path,
                transcription=context.transcription,
                duration_sec=context.validation["duration_sec"],
            )
        except Exception as exc:
            print(f"[MetricsService] Calculator pipeline failed: {exc}")
            return {
                "linguistic": {"error": str(exc)},
                "acoustic": {"error": str(exc)},
            }

    def _build_snapshot(
        self,
        context: PipelineContext,
        calculator_outputs: dict[str, dict[str, Any]],
    ) -> SnapshotRecord:
        linguistic = calculator_outputs.get("linguistic", {})
        acoustic = calculator_outputs.get("acoustic", {})
        return SnapshotRecord(
            event={
                "time": context.event.created_at,
                "day": context.event.day,
            },
            source_file=context.audio_path.name,
            transcript=context.transcription.get("text", ""),
            metrics={
                "temporal": (linguistic or {}).get("temporal", {}),
                "lexical": (linguistic or {}).get("lexical", {}),
                "prosody": (acoustic or {}).get("prosody", {}),
                "spectral": (acoustic or {}).get("spectral", {}),
            },
        )

    def _persist_snapshot(self, audio_path: Path, snapshot: SnapshotRecord) -> Path:
        event_time = (snapshot.event or {}).get(
            "time", datetime.utcnow().isoformat(timespec="seconds")
        )
        safe_time = (
            str(event_time)
            .replace(":", "")
            .replace("-", "")
            .replace("+", "_")
            .replace("Z", "")
        )
        filename = f"{safe_time}_{audio_path.stem}_{int(time.time() * 1000)}.json"
        output_path = self.snapshots_dir / filename
        write_json(output_path, snapshot.to_dict())
        return output_path

    @staticmethod
    def _wait_for_stable_file(
        path: Path,
        max_wait_sec: float = 5.0,
        poll_interval_sec: float = 0.25,
    ) -> bool:
        start = time.time()
        prev_size = -1
        stable_count = 0
        while time.time() - start < max_wait_sec:
            if not path.exists():
                return False
            size = path.stat().st_size
            if size == prev_size and size > 0:
                stable_count += 1
                if stable_count >= 2:
                    return True
            else:
                stable_count = 0
            prev_size = size
            time.sleep(poll_interval_sec)
        return False


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Watchdog-driven metrics extractor")
    parser.add_argument(
        "--incoming-dir",
        default=str(root / "data" / "incoming"),
        help="Directory to watch for .wav files",
    )
    parser.add_argument(
        "--snapshots-dir",
        default=str(root / "data" / "snapshots"),
        help="Directory for snapshot JSON outputs",
    )
    parser.add_argument(
        "--events-log",
        default=str(root / "data" / "events" / "new_audio_events.jsonl"),
        help="JSONL event log file path",
    )
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size",
    )
    parser.add_argument(
        "--keep-audio",
        action="store_true",
        help="Keep source audio after extraction (privacy delete disabled)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    watchdog_classes = _load_watchdog_classes()
    file_system_event_handler = watchdog_classes["FileSystemEventHandler"]
    observer_cls = watchdog_classes["Observer"]

    incoming_dir = Path(args.incoming_dir)
    snapshots_dir = Path(args.snapshots_dir)
    events_log = Path(args.events_log)

    incoming_dir.mkdir(parents=True, exist_ok=True)
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    events_log.parent.mkdir(parents=True, exist_ok=True)

    processor = MetricsProcessor(
        snapshots_dir=snapshots_dir,
        events_log=events_log,
        whisper_model=args.model,
        delete_source=not args.keep_audio,
    )

    worker_thread = threading.Thread(target=processor.run_worker_loop, daemon=True)
    worker_thread.start()

    class WatchdogHandler(file_system_event_handler):  # type: ignore[misc,valid-type]
        def __init__(self, wrapped: NewAudioHandler):
            super().__init__()
            self.wrapped = wrapped

        def on_created(self, event: Any) -> None:
            self.wrapped.on_created(event)

    observer = observer_cls()
    observer.schedule(
        WatchdogHandler(NewAudioHandler(processor)),
        path=str(incoming_dir),
        recursive=False,
    )
    observer.start()

    print(f"[MetricsService] Watching {incoming_dir}")
    print(f"[MetricsService] Writing snapshots to {snapshots_dir}")
    print("[MetricsService] Press Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[MetricsService] Shutting down...")
    finally:
        processor.stop_event.set()
        observer.stop()
        observer.join()
        worker_thread.join(timeout=2)


def _load_watchdog_classes() -> dict[str, Any]:
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing dependency 'watchdog'. Install analysis/environment.yml."
        ) from exc

    return {
        "FileSystemEventHandler": FileSystemEventHandler,
        "Observer": Observer,
    }


if __name__ == "__main__":
    main()

# Localhost Demo

Watchdog-first local pipeline for speech-health metrics:

1. `metrics_service`: watches `data/incoming/` for new `.wav`, extracts metrics, writes snapshot JSON, deletes source audio.
2. `aggregator`: computes rolling windows, baseline, and percentage deviations from snapshots.
3. `dashboard`: Streamlit UI that visualizes trends and transcript logs.

## Folder Layout

```text
localhost_demo/
  services/
    contracts.py
    metrics_service.py
    aggregator.py
  dashboard/
    app.py
  config/
    settings.example.json
  data/
    incoming/
    snapshots/
    aggregates/
    events/
```

## Quick Start

From repository root:

```bash
# 1) Start metrics service (watchdog + extraction)
python -m localhost_demo.services.metrics_service

# 2) Start rolling aggregator in a second terminal
python -m localhost_demo.services.aggregator

# 3) Start dashboard in a third terminal
streamlit run localhost_demo/dashboard/app.py
```

Drop `.wav` files into `localhost_demo/data/incoming/`.

## Validation Checkpoints

- Incoming file appears in `data/incoming/` and is detected in `data/events/new_audio_events.jsonl`
- Snapshot JSON is created in `data/snapshots/`
- Source `.wav` is deleted after successful extraction
- Aggregator refreshes `data/aggregates/current.json`
- Dashboard charts and conversation log update

## Event + Snapshot Contracts

- `new-audio-event` (JSONL in `data/events/new_audio_events.jsonl`)
  - `event_id`, `audio_path`, `created_at`, `day`, `source`, `received_at`, `file_size_bytes`
- `snapshot` (JSON per utterance in `data/snapshots/`)
  - event metadata + transcript + lexical/temporal metrics + acoustic metrics + validation
- Contract schema files:
  - `config/snapshot.schema.json`
  - `config/aggregate.schema.json`

## Notes

- The service reuses existing analysis modules under `analysis/` for transcription and core metric computation.
- Snapshot schema includes transcript, lexical/temporal metrics, acoustic metrics, and event metadata.
- Keep this pipeline separate from `script.py` live conversational loop.

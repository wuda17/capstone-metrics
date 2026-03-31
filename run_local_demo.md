Drop WAV files into localhost_demo/data/incoming/

```
# Metrics watcher
python -m localhost_demo.services.metrics_service

# Aggregator
python -m localhost_demo.services.aggregator

# Terminal 1 — API
export GEMINI_API_KEY=""
PATIENT_NAME=""
python -m uvicorn localhost_demo.api:app --reload --port 8000

# Terminal 2 — Frontend
cd localhost_demo/frontend && npm run dev
```

```
python -m localhost_demo.services.metrics_service
python -m localhost_demo.services.aggregator
streamlit run localhost_demo/dashboard/app.py
```

Drop WAV files into localhost_demo/data/incoming/

# Terminal 1 — API

python -m uvicorn localhost_demo.api:app --reload --port 8000

# Terminal 2 — Frontend

cd localhost_demo/frontend && npm run dev

# → open http://localhost:5173

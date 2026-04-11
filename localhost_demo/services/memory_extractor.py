"""LLM-based memory extraction — distils transcripts into typed memories."""
from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any

_PROMPT = """\
You are extracting structured memories from a speech transcript of an elderly patient named {patient_name}.

Extract meaningful memories. Each should be one of:
- "event": something that happened, including everyday routines and activities (a visit, call, meal, walk, TV show)
- "fact": a stable truth about {patient_name}'s world (family members, health conditions, preferences, history)
- "mood": an emotional state {patient_name} expressed

Return ONLY a JSON array, no other text. Each object:
{{
  "type": "event" | "fact" | "mood",
  "content": "one clear sentence capturing the memory",
  "valence": <float -1 to 1 for moods, null for events/facts>,
  "keywords": ["2-4 key terms"]
}}

Include everyday moments — meals, TV, short walks, phone calls, small chores — not just significant events.
Extract 3–6 memories per transcript, preferring more over fewer.
Keep each memory content to under 10 words.
Good examples:
  event: "Had morning coffee and watched the news"
  event: "Daughter Sarah called to check in"
  fact:  "Emily prefers tea over coffee"
  mood:  "Felt a bit tired after lunch" (valence ≈ -0.2)

Transcript date: {date}
Transcript: "{text}"
"""


class MemoryExtractor:
    def __init__(self, patient_name: str = "Emily") -> None:
        self._model: Any = None
        self.patient_name = patient_name

    def extract(self, text: str, event_time: str, date: str) -> list[dict]:
        model = self._get_model()
        if model:
            result = self._llm_extract(model, text, event_time, date)
            if result:
                return result
        # LLM unavailable or failed — caller can provide pre-written fallback
        return []

    def _llm_extract(self, model: Any, text: str, event_time: str, date: str) -> list[dict]:
        prompt = _PROMPT.format(patient_name=self.patient_name, text=text, date=date)
        try:
            resp = model.generate_content(prompt)
            raw = resp.text.strip()
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if not match:
                return []
            items = json.loads(match.group())
            return [self._normalise(m, event_time, date, text) for m in items if isinstance(m, dict)]
        except Exception as exc:
            print(f"[MemoryExtractor] LLM extraction failed: {exc}")
            return []

    @staticmethod
    def _normalise(raw: dict, event_time: str, date: str, source_text: str) -> dict:
        mem_type = raw.get("type", "event")
        if mem_type not in ("event", "fact", "mood"):
            mem_type = "event"
        return {
            "id": f"m_{uuid.uuid4().hex[:10]}",
            "type": mem_type,
            "content": str(raw.get("content", "")).strip(),
            "valence": raw.get("valence"),  # None for non-moods
            "keywords": raw.get("keywords", []),
            "date": date,
            "source_event_time": event_time,
            "source_text": source_text,
        }

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model if self._model is not False else None
        try:
            import google.generativeai as genai
            key = os.environ.get("GEMINI_API_KEY")
            if not key:
                self._model = False
                return None
            genai.configure(api_key=key)
            self._model = genai.GenerativeModel("gemini-2.5-flash")
            return self._model
        except ImportError:
            self._model = False
            return None

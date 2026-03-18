"""FerbAI chatbot — RAG-based caretaker assistant powered by Gemini."""
from __future__ import annotations

import json as _json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from localhost_demo.services.memory_service import MemoryService

_SYSTEM = (
    "You are FerbAI, a compassionate AI assistant helping caretakers understand "
    "and monitor their patient's wellbeing through speech and language pattern analysis. "
    "You have access to recent transcripts from Emily (the patient). Be warm, "
    "concise, and clinically insightful. Highlight meaningful patterns and trends. "
    "When asked for summaries, organise by time period. Keep responses under 200 words "
    "unless a detailed summary is requested."
)


class ChatService:
    def __init__(self, memory_service: MemoryService) -> None:
        self.memory = memory_service
        self._model: Any = None

    def respond(self, message: str) -> dict[str, Any]:
        context_items = self.memory.search(message, top_k=6)
        context_str = "\n\n".join(
            f"[{t['event_time']}]\n{t['text']}" for t in context_items
        ) or "(no transcripts available yet — start recording to build Emily's history)"

        model = self._get_model()
        if not model:
            return {
                "response": (
                    "FerbAI needs a Gemini API key. Get one free at "
                    "https://aistudio.google.com, then set it:\n\n"
                    "  export GEMINI_API_KEY=your_key_here\n\n"
                    "Also run: pip install google-generativeai"
                ),
                "sources": [],
            }

        prompt = (
            f"{_SYSTEM}\n\n"
            f"Recent transcripts from Emily:\n\n{context_str}\n\n"
            f"Caretaker question: {message}"
        )

        try:
            resp = model.generate_content(prompt)
            return {
                "response": resp.text,
                "sources": [t["event_time"] for t in context_items],
            }
        except Exception as exc:
            return {
                "response": f"FerbAI encountered an error: {exc}",
                "sources": [],
            }

    def get_summaries(self) -> dict[str, str]:
        """Return LLM-generated summaries for today, this week, and this month."""
        transcripts = self.memory.get_all_transcripts()
        now = datetime.now(timezone.utc)

        def _corpus(days: int) -> str:
            cutoff = now - timedelta(days=days)
            items = []
            for t in transcripts:
                try:
                    ts_str = t.get("event_time", "").replace("Z", "+00:00")
                    ts = datetime.fromisoformat(ts_str)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts.astimezone(timezone.utc) >= cutoff:
                        items.append(t)
                except (ValueError, AttributeError):
                    continue
            if not items:
                return "(no conversations recorded in this period)"
            return "\n\n".join(
                f"[{t.get('event_time', '')[:10]}] {t.get('text', '').strip()}"
                for t in items
            )

        model = self._get_model()
        if not model:
            msg = "Gemini API key not configured — set GEMINI_API_KEY to enable summaries."
            return {"today": msg, "week": msg, "month": msg}

        prompt = (
            "You are FerbAI, an AI assistant helping a caretaker monitor Emily, an elderly patient.\n\n"
            f"PAST 24 HOURS:\n{_corpus(1)[:1500]}\n\n"
            f"PAST 7 DAYS:\n{_corpus(7)[:2000]}\n\n"
            f"PAST 30 DAYS:\n{_corpus(30)[:2500]}\n\n"
            "Return a JSON object with exactly these three keys. Each value must be 2-3 sentences "
            "of warm, professional prose for a caretaker — covering wellbeing, notable events, "
            "mood patterns, and any concerns worth flagging.\n\n"
            '{"today": "...", "week": "...", "month": "..."}\n\n'
            "Return ONLY valid JSON. No markdown, no extra text."
        )
        try:
            raw = self._get_model().generate_content(prompt).text.strip()
            # Strip markdown code fences if Gemini wraps the response
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = _json.loads(raw)
            return {
                "today": str(parsed.get("today", "")),
                "week":  str(parsed.get("week",  "")),
                "month": str(parsed.get("month", "")),
            }
        except Exception as exc:
            msg = f"Could not generate summary: {exc}"
            return {"today": msg, "week": msg, "month": msg}

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
            self._model = genai.GenerativeModel("gemini-1.5-flash")
            return self._model
        except ImportError:
            self._model = False
            return None

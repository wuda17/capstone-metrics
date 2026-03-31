"""FerbAI chatbot — RAG-based caretaker assistant powered by Gemini."""
from __future__ import annotations

import json as _json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from localhost_demo.services.memory_service import MemoryService

def _build_system_prompt(patient_name: str) -> str:
    return (
        f"You are Ferb, a clinical AI assistant helping caretakers monitor {patient_name}'s wellbeing "
        "through speech and conversation analysis. "
        f"Always weave in at least one recent observation or notable event from {patient_name}'s transcripts, "
        "even during casual or conversational exchanges (greetings, thanks, small talk). "
        "For casual messages, keep the tone warm and natural but still surface a brief, relevant "
        "highlight — e.g. a recent mood, activity, or anything worth a caretaker's attention. "
        "For clinical questions, lead with the key finding, support with 2-3 specific observations "
        "from the transcripts, and use brief markdown (bold key terms, short bullet lists where "
        "helpful). Flag concerns clearly but without alarm. "
        "Keep all responses under 120 words. Never pad — if the answer is short, keep it short."
    )


class ChatService:
    def __init__(self, memory_service: MemoryService, patient_name: str = "Emily") -> None:
        self.memory = memory_service
        self.patient_name = patient_name
        self._system = _build_system_prompt(patient_name)
        self._model: Any = None

    def respond(self, message: str) -> dict[str, Any]:
        context_items = self.memory.search(message, top_k=6)
        context_str = "\n\n".join(
            f"[{t['event_time']}]\n{t['text']}" for t in context_items
        ) or f"(no transcripts available yet — start recording to build {self.patient_name}'s history)"

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
            f"{self._system}\n\n"
            f"Recent transcripts from {self.patient_name}:\n\n{context_str}\n\n"
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
            f"You are FerbAI, an AI assistant helping a caretaker monitor {self.patient_name}, an elderly patient.\n\n"
            f"PAST 24 HOURS:\n{_corpus(1)[:1500]}\n\n"
            f"PAST 7 DAYS:\n{_corpus(7)[:2000]}\n\n"
            f"PAST 30 DAYS:\n{_corpus(30)[:2500]}\n\n"
            "Return a JSON object with exactly these three keys. Each value must be 1 sentence maximum "
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
            self._model = genai.GenerativeModel("gemini-2.5-flash")
            return self._model
        except ImportError:
            self._model = False
            return None

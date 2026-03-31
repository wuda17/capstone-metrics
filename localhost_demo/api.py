"""FerbAI backend API — serves aggregate data and chatbot to the React frontend."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from localhost_demo.services.memory_service import MemoryService
from localhost_demo.services.chat_service import ChatService

_BASE     = Path(__file__).parent
_AGG      = _BASE / "data" / "aggregates"
_SNAP     = _BASE / "data" / "snapshots"
_INCOMING = _BASE / "data" / "incoming"

app = FastAPI(title="FerbAI API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_PATIENT_NAME = os.environ.get("PATIENT_NAME", "Emily")

_mem: MemoryService | None = None
_chat: ChatService | None = None
_summary_cache: dict = {}
_SUMMARY_TTL = 1800  # 30 minutes


def _memory() -> MemoryService:
    global _mem
    if _mem is None:
        _mem = MemoryService(_SNAP, _AGG, patient_name=_PATIENT_NAME)
    return _mem


def _chatbot() -> ChatService:
    global _chat
    if _chat is None:
        _chat = ChatService(_memory(), patient_name=_PATIENT_NAME)
    return _chat


@app.get("/api/current")
def get_current():
    p = _AGG / "current.json"
    if not p.exists():
        raise HTTPException(404, "current.json not found")
    return json.loads(p.read_text())


@app.get("/api/history")
def get_history(limit: int = 200):
    p = _AGG / "history.jsonl"
    if not p.exists():
        return []
    lines = [ln for ln in p.read_text().splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines[-limit:]]


@app.get("/api/memories")
def get_memories():
    return _memory().get_memories()


@app.post("/api/memories/refresh")
def refresh_memories(force: bool = False):
    """Extract memories from any unprocessed transcripts using Gemini.
    Set force=true to re-extract all transcripts."""
    return _memory().refresh_memories(force=force)


@app.get("/api/summary")
def get_summary(force: bool = True):
    """LLM-generated summaries for today, this week, and this month.
    Cached for 30 minutes; pass ?force=true to regenerate immediately."""
    global _summary_cache
    if not force and _summary_cache.get("ts", 0) + _SUMMARY_TTL > time.time():
        return _summary_cache["data"]
    result = _chatbot().get_summaries()
    _summary_cache = {"ts": time.time(), "data": result}
    return result


@app.get("/api/status")
def get_status():
    """Returns whether WAV files are queued for processing in the incoming directory."""
    wav_files = list(_INCOMING.glob("*.wav")) if _INCOMING.exists() else []
    return {"recording": len(wav_files) > 0, "queued_count": len(wav_files)}


class ChatReq(BaseModel):
    message: str


@app.post("/api/chat")
def chat(req: ChatReq):
    return _chatbot().respond(req.message)

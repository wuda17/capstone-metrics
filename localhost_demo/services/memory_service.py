"""Memory service — typed memory graph built from extracted memories."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    _SKLEARN = True
except ImportError:
    _SKLEARN = False

# Edge drawn when combined similarity exceeds this
SIMILARITY_THRESHOLD = 0.10

# Co-session memories always get at least this edge weight
CO_SESSION_WEIGHT = 0.35

NODE_COLORS = {
    "event": "#14c8a8",   # teal
    "fact":  "#7c6af7",   # purple
}

def _mood_color(valence: float | None) -> str:
    v = valence or 0
    if v > 0.3:  return "#22c87e"   # positive → green
    if v < -0.3: return "#ef4545"   # negative → red
    return "#f5a623"                 # neutral  → amber


class MemoryService:
    def __init__(self, snapshots_dir: Path, aggregates_dir: Path) -> None:
        self.snapshots_dir = snapshots_dir
        self.aggregates_dir = aggregates_dir
        self._memories_path = aggregates_dir.parent / "memories.json"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def get_memories(self) -> dict[str, Any]:
        memories = self.load_memories()
        facts = [m for m in memories if m.get("type") == "fact"]
        ref_counts = self._compute_reference_counts(facts, memories)
        graph = {
            "nodes": [self._to_node(m, ref_counts.get(m["id"], 1)) for m in facts],
            "links": self._compute_links(facts),
        }
        return {"graph": graph, "timeline": self._build_timeline(memories)}

    def search(self, query: str, top_k: int = 6) -> list[dict]:
        """Return top-k most relevant transcripts for RAG (searches source text)."""
        transcripts = self._collect_transcripts()
        if not transcripts:
            return []
        if not _SKLEARN or len(transcripts) < 2:
            return transcripts[:top_k]
        texts = [t["text"] for t in transcripts]
        try:
            vec = TfidfVectorizer(max_features=500, stop_words="english")
            mat = vec.fit_transform(texts + [query])
            sims = cosine_similarity(mat[-1], mat[:-1])[0]
            return [transcripts[i] for i in sims.argsort()[::-1][:top_k]]
        except ValueError:
            return transcripts[:top_k]

    def get_all_transcripts(self) -> list[dict]:
        return self._collect_transcripts()

    # ------------------------------------------------------------------ #
    # Memory storage
    # ------------------------------------------------------------------ #

    def load_memories(self) -> list[dict]:
        if not self._memories_path.exists():
            return []
        try:
            data = json.loads(self._memories_path.read_text(encoding="utf-8"))
            return data.get("memories", [])
        except (json.JSONDecodeError, KeyError):
            return []

    def save_memories(self, memories: list[dict]) -> None:
        from datetime import datetime, timezone
        self._memories_path.parent.mkdir(parents=True, exist_ok=True)
        self._memories_path.write_text(
            json.dumps({"version": "1.0", "updated_at": datetime.now(timezone.utc).isoformat(), "memories": memories}, indent=2),
            encoding="utf-8",
        )

    def add_memories(self, new_memories: list[dict]) -> None:
        existing = self.load_memories()
        existing_ids = {m["id"] for m in existing}
        to_add = [m for m in new_memories if m["id"] not in existing_ids]
        self.save_memories(existing + to_add)

    def refresh_memories(self, force: bool = False) -> dict[str, int]:
        """Extract memories for any transcripts not yet processed."""
        from localhost_demo.services.memory_extractor import MemoryExtractor
        extractor = MemoryExtractor()
        transcripts = self._collect_transcripts()
        existing = self.load_memories()
        done_times = {m["source_event_time"] for m in existing}

        new: list[dict] = []
        for t in transcripts:
            et = t.get("event_time", "")
            if not force and et in done_times:
                continue
            extracted = extractor.extract(t["text"], et, t.get("day", ""))
            new.extend(extracted)

        if new:
            self.add_memories(new)
        return {"extracted": len(new), "total": len(self.load_memories())}

    # ------------------------------------------------------------------ #
    # Graph construction
    # ------------------------------------------------------------------ #

    @staticmethod
    def _compute_reference_counts(facts: list[dict], all_memories: list[dict]) -> dict[str, int]:
        """For each fact, count how many other memories share at least one keyword with it."""
        counts: dict[str, int] = {}
        for fact in facts:
            fact_kw = {k.lower() for k in fact.get("keywords", [])}
            if not fact_kw:
                counts[fact["id"]] = 1
                continue
            count = sum(
                1 for mem in all_memories
                if mem["id"] != fact["id"]
                and fact_kw & {k.lower() for k in mem.get("keywords", [])}
            )
            counts[fact["id"]] = max(1, count)
        return counts

    @staticmethod
    def _to_node(m: dict, ref_count: int = 1) -> dict:
        mem_type = m.get("type", "event")
        color = _mood_color(m.get("valence")) if mem_type == "mood" else NODE_COLORS.get(mem_type, "#7c6af7")
        keywords = m.get("keywords", [])
        # Size: base 7, scales with references, capped at 22
        size = round(min(7 + ref_count * 2.0, 22), 1)
        return {
            "id": m["id"],
            "type": mem_type,
            "content": m.get("content", ""),
            "date": m.get("date", ""),
            "source_event_time": m.get("source_event_time", ""),
            "source_text": m.get("source_text", ""),
            "valence": m.get("valence"),
            "keywords": keywords,
            "primary_keyword": keywords[0] if keywords else "",
            "reference_count": ref_count,
            "color": color,
            "size": size,
        }

    def _build_timeline(self, memories: list[dict]) -> list[dict]:
        """Cluster events and moods by keyword overlap; compute recurrence_count."""
        items = [m for m in memories if m.get("type") in ("event", "mood")]
        items.sort(key=lambda m: m.get("source_event_time", ""))

        clusters: list[dict] = []
        for mem in items:
            kw = {k.lower() for k in mem.get("keywords", [])}
            mem_type = mem.get("type")

            # Find the existing cluster of the same type with the most keyword overlap
            best_idx, best_overlap = -1, 0
            for ci, c in enumerate(clusters):
                if c["type"] != mem_type:
                    continue
                overlap = len(kw & set(c["_kw_union"]))
                if overlap > best_overlap:
                    best_overlap, best_idx = overlap, ci

            instance = {
                "id": mem["id"],
                "date": mem.get("date", ""),
                "source_event_time": mem.get("source_event_time", ""),
                "source_text": mem.get("source_text", ""),
                "content": mem.get("content", ""),
            }

            if best_idx >= 0 and best_overlap >= 1:
                c = clusters[best_idx]
                c["recurrence_count"] += 1
                c["dates"].append(mem.get("date", ""))
                c["instances"].append(instance)
                c["_kw_union"] = list(set(c["_kw_union"]) | kw)
                # Promote most recent instance as representative
                if mem.get("source_event_time", "") > c["source_event_time"]:
                    c.update({
                        "source_event_time": mem.get("source_event_time", ""),
                        "source_text": mem.get("source_text", ""),
                        "content": mem.get("content", ""),
                        "valence": mem.get("valence"),
                    })
            else:
                clusters.append({
                    "id": mem["id"],
                    "type": mem_type,
                    "content": mem.get("content", ""),
                    "valence": mem.get("valence"),
                    "keywords": mem.get("keywords", []),
                    "recurrence_count": 1,
                    "dates": [mem.get("date", "")],
                    "source_event_time": mem.get("source_event_time", ""),
                    "source_text": mem.get("source_text", ""),
                    "instances": [instance],
                    "_kw_union": list(kw),
                })

        for c in clusters:
            del c["_kw_union"]

        clusters.sort(key=lambda c: min(c["dates"]) if c["dates"] else "")
        return clusters

    def _compute_links(self, memories: list[dict]) -> list[dict]:
        if len(memories) < 2:
            return []

        contents = [m.get("content", "") for m in memories]
        keyword_sets = [set(kw.lower() for kw in m.get("keywords", [])) for m in memories]

        # TF-IDF cosine similarity
        tfidf_sim: list[list[float]] = []
        if _SKLEARN:
            try:
                vec = TfidfVectorizer(max_features=500, stop_words="english")
                mat = vec.fit_transform(contents)
                sim_mat = cosine_similarity(mat)
                tfidf_sim = sim_mat.tolist()
            except ValueError:
                tfidf_sim = [[0.0] * len(memories)] * len(memories)
        else:
            tfidf_sim = [[0.0] * len(memories)] * len(memories)

        links = []
        for i in range(len(memories)):
            for j in range(i + 1, len(memories)):
                mi, mj = memories[i], memories[j]

                # Keyword Jaccard overlap
                ki, kj = keyword_sets[i], keyword_sets[j]
                jaccard = len(ki & kj) / len(ki | kj) if (ki | kj) else 0.0

                # TF-IDF
                tfidf = tfidf_sim[i][j] if tfidf_sim else 0.0

                # Co-session bonus
                co_session = mi.get("source_event_time") == mj.get("source_event_time")

                combined = (tfidf + jaccard) / 2
                if co_session:
                    combined = max(combined, CO_SESSION_WEIGHT)

                if combined > SIMILARITY_THRESHOLD:
                    links.append({
                        "source": mi["id"],
                        "target": mj["id"],
                        "value": round(combined, 3),
                        "co_session": co_session,
                    })
        return links

    # ------------------------------------------------------------------ #
    # Transcript helpers (for RAG search)
    # ------------------------------------------------------------------ #

    def _collect_transcripts(self) -> list[dict]:
        seen: set[str] = set()
        items: list[dict] = []

        history_path = self.aggregates_dir / "history.jsonl"
        if history_path.exists():
            for line in history_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    for t in self._extract_transcripts(entry):
                        key = t.get("event_time", "")
                        if key and key not in seen:
                            seen.add(key)
                            items.append(t)
                except json.JSONDecodeError:
                    continue

        current_path = self.aggregates_dir / "current.json"
        if current_path.exists():
            try:
                entry = json.loads(current_path.read_text(encoding="utf-8"))
                for t in self._extract_transcripts(entry):
                    key = t.get("event_time", "")
                    if key and key not in seen:
                        seen.add(key)
                        items.append(t)
            except (json.JSONDecodeError, KeyError):
                pass

        items.sort(key=lambda x: x.get("event_time", ""))
        return items

    @staticmethod
    def _extract_transcripts(entry: dict) -> list[dict]:
        block = entry.get("transcripts") or entry.get("latest_transcripts")
        if isinstance(block, dict):
            return block.get("items", [])
        if isinstance(block, list):
            return block
        return []

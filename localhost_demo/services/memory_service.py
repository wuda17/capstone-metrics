"""Memory service — typed memory graph built from extracted memories."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

# ── NLP imports (all optional, graceful fallback) ──────────────────────────────
try:
    from nltk.stem import PorterStemmer as _PorterStemmer
    _stemmer = _PorterStemmer()
    _NLTK = True
except Exception:
    _stemmer = None
    _NLTK = False

try:
    from gensim import corpora as _corpora
    from gensim.models import TfidfModel as _TfidfModel
    from gensim.similarities import SparseMatrixSimilarity as _SparseSim
    _GENSIM = True
except Exception:
    _GENSIM = False

# Keep sklearn as fallback for the RAG search method
try:
    from sklearn.feature_extraction.text import TfidfVectorizer as _TfidfVec
    from sklearn.metrics.pairwise import cosine_similarity as _cos_sim
    _SKLEARN = True
except ImportError:
    _SKLEARN = False

# ── Thresholds ─────────────────────────────────────────────────────────────────
SIMILARITY_THRESHOLD = 0.10   # edge drawn when combined score > this
CO_SESSION_WEIGHT    = 0.35   # co-session bonus floor
DEDUP_THRESHOLD      = 0.62   # combined score above which two facts merge

# ── Category system ────────────────────────────────────────────────────────────
_CATEGORY_COLORS = {
    "people":     "#d4856a",   # warm terracotta
    "health":     "#6aaa82",   # sage green
    "activity":   "#d4a84b",   # warm amber-gold
    "place":      "#5a9eb5",   # dusty slate-blue
    "preference": "#a07ab5",   # soft mauve
}

_PEOPLE_ROLES = {
    'daughter', 'son', 'sister', 'brother', 'mother', 'father',
    'husband', 'wife', 'friend', 'grandson', 'granddaughter',
    'grandchildren', 'niece', 'nephew', 'aunt', 'uncle',
    'neighbour', 'neighbor', 'partner', 'carer', 'nurse', 'doctor',
}
_HEALTH_KW = {
    'blood pressure', 'health', 'medication', 'pain', 'sleep',
    'tired', 'fatigue', 'exercise', 'diet', 'salt', 'chamomile',
    'back', 'fall', 'injury', 'therapy', 'supplement', 'prescription',
    'tablet', 'pill', 'surgery', 'physio', 'gp', 'clinic', 'hospital',
    'knee', 'walk', 'walking', 'stretching', 'breathing',
}
_ACTIVITY_KW = {
    'baking', 'cooking', 'dancing', 'reading', 'gardening',
    'knitting', 'sewing', 'swimming', 'yoga', 'sport', 'hobby',
    'craft', 'music', 'singing', 'painting', 'writing', 'crossword',
    'puzzle', 'game', 'learning', 'fishing', 'book', 'book club',
    'documentary', 'television', 'recipe',
}
_PLACE_KW = {
    'garden', 'park', 'coast', 'sea', 'village', 'church', 'hall',
    'shop', 'market', 'holiday', 'portugal', 'france', 'london',
    'kitchen', 'beach', 'lake', 'forest', 'town', 'city', 'river',
    'village hall',
}
_PREFERENCE_KW = {
    'favourite', 'favorite', 'love', 'enjoy', 'prefer', 'like',
    'tradition', 'walnuts', 'banana', 'penguins', 'memory', 'always',
    'never', 'usually', 'sunday', 'weekly', 'annual', 'history',
}

NODE_COLORS = {
    "event": "#14c8a8",
    "fact":  "#d4856a",   # default people/warm if category not resolved
}


# ── Module-level helpers ───────────────────────────────────────────────────────

def _mood_color(valence: float | None) -> str:
    v = valence or 0
    if v > 0.3:  return "#22c87e"
    if v < -0.3: return "#ef4545"
    return "#f5a623"


def _stem(word: str) -> str:
    """Stem a single word; falls back to lower() if NLTK unavailable."""
    if _NLTK and _stemmer is not None:
        return _stemmer.stem(word.lower())
    return word.lower()


def _categorize(content: str, keywords: list[str]) -> str:
    """Assign one of 5 categories to a fact node."""
    kw_lower = {k.lower() for k in keywords}
    # Health wins over activity (e.g. 'walking' could be both — health context wins)
    if kw_lower & _HEALTH_KW:    return "health"
    if kw_lower & _PLACE_KW:     return "place"
    if kw_lower & _PEOPLE_ROLES: return "people"
    if kw_lower & _ACTIVITY_KW:  return "activity"
    if kw_lower & _PREFERENCE_KW: return "preference"
    # Heuristic: relational language → people
    c = content.lower()
    if any(t in c for t in ('named', 'her ', 'his ', 'their ', "'s ")):
        return "people"
    return "preference"


def _make_enriched_doc(m: dict) -> list[str]:
    """
    Build a stemmed token list from content + keywords + source_text snippet.
    Used as input to gensim TF-IDF.
    """
    text = (
        m.get("content", "") + " "
        + " ".join(m.get("keywords", [])) + " "
        + m.get("source_text", "")[:150]
    )
    tokens = re.findall(r"[a-z]{3,}", text.lower())
    return [_stem(t) for t in tokens]


def _build_tfidf_sim_matrix(facts: list[dict]) -> list[list[float]]:
    """
    Compute NxN cosine similarity matrix using gensim TF-IDF on enriched documents.
    Returns a zero matrix if gensim is unavailable or corpus is too small.
    """
    n = len(facts)
    zero: list[list[float]] = [[0.0] * n for _ in range(n)]
    if not _GENSIM or n < 2:
        return zero
    try:
        docs = [_make_enriched_doc(f) for f in facts]
        dct = _corpora.Dictionary(docs)
        if len(dct) == 0:
            return zero
        corpus = [dct.doc2bow(d) for d in docs]
        tfidf = _TfidfModel(corpus)
        tfidf_corpus = list(tfidf[corpus])
        idx = _SparseSim(tfidf_corpus, num_features=len(dct))
        sim_matrix = [list(map(float, idx[row])) for row in tfidf_corpus]
        return sim_matrix
    except Exception as exc:
        print(f"[MemoryService] gensim TF-IDF failed: {exc}")
        return zero


class MemoryService:
    def __init__(self, snapshots_dir: Path, aggregates_dir: Path, patient_name: str = "Emily") -> None:
        self.snapshots_dir = snapshots_dir
        self.aggregates_dir = aggregates_dir
        self.patient_name = patient_name
        self._memories_path = aggregates_dir.parent / "memories.json"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def get_memories(self) -> dict[str, Any]:
        memories = self.load_memories()
        facts = [m for m in memories if m.get("type") == "fact"]
        ref_counts = self._compute_reference_counts(facts, memories)
        nodes = [self._to_node(m, ref_counts.get(m["id"], 1)) for m in facts]
        links = self._compute_links(facts)
        nodes, links = self._consolidate_nodes(nodes, links)
        return {"graph": {"nodes": nodes, "links": links}, "timeline": self._build_timeline(memories)}

    def search(self, query: str, top_k: int = 6) -> list[dict]:
        """Return top-k most relevant transcripts for RAG."""
        transcripts = self._collect_transcripts()
        if not transcripts:
            return []
        if not _SKLEARN or len(transcripts) < 2:
            return transcripts[:top_k]
        texts = [t["text"] for t in transcripts]
        try:
            vec = _TfidfVec(max_features=500, stop_words="english")
            mat = vec.fit_transform(texts + [query])
            sims = _cos_sim(mat[-1], mat[:-1])[0]
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
            json.dumps({
                "version": "1.0",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "memories": memories,
            }, indent=2),
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
        extractor = MemoryExtractor(patient_name=self.patient_name)
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
        """
        For each fact count distinct DATES across all other memories that share
        at least one stemmed keyword — session-frequency, not raw memory count.
        """
        counts: dict[str, int] = {}
        for fact in facts:
            raw_kw = fact.get("keywords", [])
            if not raw_kw:
                counts[fact["id"]] = 1
                continue
            stemmed_fact_kw = {_stem(k) for k in raw_kw}
            seen_dates: set[str] = set()
            for mem in all_memories:
                if mem["id"] == fact["id"]:
                    continue
                if stemmed_fact_kw & {_stem(k) for k in mem.get("keywords", [])}:
                    date = mem.get("date", "")
                    if date:
                        seen_dates.add(date)
            counts[fact["id"]] = max(1, len(seen_dates))
        return counts

    @staticmethod
    def _to_node(m: dict, ref_count: int = 1) -> dict:
        mem_type = m.get("type", "event")
        keywords = m.get("keywords", [])

        if mem_type == "mood":
            color = _mood_color(m.get("valence"))
            category = "mood"
        elif mem_type == "fact":
            category = _categorize(m.get("content", ""), keywords)
            color = _CATEGORY_COLORS.get(category, NODE_COLORS["fact"])
        else:
            color = NODE_COLORS.get(mem_type, "#7c6af7")
            category = mem_type

        # Longest keyword is most specific (e.g. "blood pressure" > "health")
        primary_keyword = max(keywords, key=len) if keywords else ""
        size = round(min(12 + ref_count * 2.5, 28), 1)

        return {
            "id":                m["id"],
            "type":              mem_type,
            "category":          category,
            "content":           m.get("content", ""),
            "date":              m.get("date", ""),
            "source_event_time": m.get("source_event_time", ""),
            "source_text":       m.get("source_text", ""),
            "valence":           m.get("valence"),
            "keywords":          keywords,
            "primary_keyword":   primary_keyword,
            "reference_count":   ref_count,
            "color":             color,
            "size":              size,
        }

    def _compute_links(self, facts: list[dict]) -> list[dict]:
        if len(facts) < 2:
            return []

        tfidf_sim = _build_tfidf_sim_matrix(facts)
        stemmed_kw_sets = [
            {_stem(k) for k in m.get("keywords", [])}
            for m in facts
        ]

        links = []
        for i in range(len(facts)):
            for j in range(i + 1, len(facts)):
                mi, mj = facts[i], facts[j]

                ki, kj = stemmed_kw_sets[i], stemmed_kw_sets[j]
                union = ki | kj
                jaccard = len(ki & kj) / len(union) if union else 0.0
                tfidf = tfidf_sim[i][j]
                co_session = mi.get("source_event_time") == mj.get("source_event_time")

                combined = (tfidf + jaccard) / 2
                if co_session:
                    combined = max(combined, CO_SESSION_WEIGHT)

                if combined > SIMILARITY_THRESHOLD:
                    links.append({
                        "source":     mi["id"],
                        "target":     mj["id"],
                        "value":      round(combined, 3),
                        "co_session": co_session,
                    })
        return links

    @staticmethod
    def _consolidate_nodes(
        nodes: list[dict], links: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        """
        Merge near-duplicate fact nodes at display time when combined similarity
        exceeds DEDUP_THRESHOLD. Does NOT modify memories.json.
        """
        if len(nodes) < 2:
            return nodes, links

        id_to_idx = {n["id"]: i for i, n in enumerate(nodes)}

        # Union-Find
        parent = list(range(len(nodes)))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            parent[find(a)] = find(b)

        for link in links:
            si = id_to_idx.get(link["source"])
            ti = id_to_idx.get(link["target"])
            if si is not None and ti is not None and link.get("value", 0) > DEDUP_THRESHOLD:
                union(si, ti)

        groups: dict[int, list[int]] = defaultdict(list)
        for i in range(len(nodes)):
            groups[find(i)].append(i)

        new_nodes: list[dict] = []
        id_remap: dict[str, str] = {}

        for members in groups.values():
            if len(members) == 1:
                new_nodes.append(nodes[members[0]])
                continue

            group_nodes = [nodes[i] for i in members]
            canonical = max(
                group_nodes,
                key=lambda n: (n.get("reference_count", 1), len(n.get("content", "")))
            )

            # Union keywords (preserve insertion order, deduplicate)
            seen_kw: set[str] = set()
            all_kw: list[str] = []
            for n in group_nodes:
                for k in n.get("keywords", []):
                    if k.lower() not in seen_kw:
                        seen_kw.add(k.lower())
                        all_kw.append(k)

            summed_refs = sum(n.get("reference_count", 1) for n in group_nodes)
            merged = dict(canonical)
            merged["keywords"]        = all_kw
            merged["primary_keyword"] = max(all_kw, key=len) if all_kw else canonical.get("primary_keyword", "")
            merged["reference_count"] = summed_refs
            merged["size"]            = round(min(7 + summed_refs * 2.0, 22), 1)
            new_nodes.append(merged)

            for n in group_nodes:
                if n["id"] != canonical["id"]:
                    id_remap[n["id"]] = canonical["id"]

        canonical_ids = {n["id"] for n in new_nodes}
        seen_edges: set[tuple[str, str]] = set()
        new_links: list[dict] = []
        for link in links:
            src = id_remap.get(link["source"], link["source"])
            tgt = id_remap.get(link["target"], link["target"])
            if src == tgt:
                continue
            if src not in canonical_ids or tgt not in canonical_ids:
                continue
            edge = (min(src, tgt), max(src, tgt))
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            new_links.append({**link, "source": src, "target": tgt})

        return new_nodes, new_links

    def _build_timeline(self, memories: list[dict]) -> list[dict]:
        """Cluster events and moods by keyword overlap; compute recurrence_count."""
        items = [m for m in memories if m.get("type") in ("event", "mood")]
        items.sort(key=lambda m: m.get("source_event_time", ""))

        clusters: list[dict] = []
        for mem in items:
            kw = {k.lower() for k in mem.get("keywords", [])}
            mem_type = mem.get("type")

            best_idx, best_overlap = -1, 0
            for ci, c in enumerate(clusters):
                if c["type"] != mem_type:
                    continue
                overlap = len(kw & set(c["_kw_union"]))
                if overlap > best_overlap:
                    best_overlap, best_idx = overlap, ci

            instance = {
                "id":                mem["id"],
                "date":              mem.get("date", ""),
                "source_event_time": mem.get("source_event_time", ""),
                "source_text":       mem.get("source_text", ""),
                "content":           mem.get("content", ""),
            }

            if best_idx >= 0 and best_overlap >= 1:
                c = clusters[best_idx]
                c["recurrence_count"] += 1
                c["dates"].append(mem.get("date", ""))
                c["instances"].append(instance)
                c["_kw_union"] = list(set(c["_kw_union"]) | kw)
                if mem.get("source_event_time", "") > c["source_event_time"]:
                    c.update({
                        "source_event_time": mem.get("source_event_time", ""),
                        "source_text":       mem.get("source_text", ""),
                        "content":           mem.get("content", ""),
                        "valence":           mem.get("valence"),
                    })
            else:
                clusters.append({
                    "id":               mem["id"],
                    "type":             mem_type,
                    "content":          mem.get("content", ""),
                    "valence":          mem.get("valence"),
                    "keywords":         mem.get("keywords", []),
                    "recurrence_count": 1,
                    "dates":            [mem.get("date", "")],
                    "source_event_time": mem.get("source_event_time", ""),
                    "source_text":      mem.get("source_text", ""),
                    "instances":        [instance],
                    "_kw_union":        list(kw),
                })

        for c in clusters:
            del c["_kw_union"]

        clusters.sort(key=lambda c: min(c["dates"]) if c["dates"] else "")
        return clusters

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

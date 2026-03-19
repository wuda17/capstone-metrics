"""Generate realistic mock snapshot + memory data for the FerbAI dashboard."""
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

random.seed(42)

SNAPSHOTS_DIR      = Path("localhost_demo/data/snapshots")
AGGREGATES_DIR     = Path("localhost_demo/data/aggregates")
MEMORIES_PATH      = Path("localhost_demo/data/memories.json")
DAILY_CACHE_PATH   = Path("localhost_demo/data/daily_lexical.json")

# ── Transcripts ───────────────────────────────────────────────────────────────

TRANSCRIPTS = [
    "Today I went to the park with my daughter Sarah. The weather was just beautiful, really lovely. We fed the ducks and had ice cream after. It was a really nice afternoon, I felt very relaxed.",
    "I've been feeling a bit tired lately, not sleeping as well as I used to. Woke up a few times last night. Maybe I should try that chamomile tea again. I think the heat has been affecting me.",
    "Had a wonderful phone call with my sister Margaret this morning. She told me about her garden and how the tomatoes are doing really well this year. We laughed so much, it was lovely to catch up.",
    "The doctor's appointment went alright. He said my blood pressure is a little high but nothing too concerning. I just need to watch my salt intake and keep walking every day. I feel okay about it.",
    "I watched that documentary about penguins last night. It was absolutely fascinating, I didn't know they could swim so fast. I told Michael about it and he wants to watch it too.",
    "Tried a new recipe for chicken soup today. Added some ginger and it turned out quite good. The kitchen smelled wonderful. I might make it again next week for when the grandchildren visit.",
    "Been thinking about my mother a lot today. She would have turned eighty-three this week. I miss her very much. We used to bake together every Sunday morning when I was young.",
    "Went for my morning walk along the river path. Saw a heron standing very still by the water. Walked for about forty minutes. My knee was a bit stiff at the start but got better.",
    "My grandson Tommy called me on video today. He's learning to read now and read me a whole page from his book. I was so proud of him. Children pick things up so quickly, it is remarkable.",
    "I sorted through some old photographs this afternoon. Found pictures from our holiday in Portugal, must have been nineteen eighty-seven. So many good memories. I should put them in an album.",
    "Felt a bit anxious this morning, not sure why. Just a general feeling of unease. I did my breathing exercises and that helped a little. Had a cup of tea and sat in the garden for a while.",
    "Book club was lovely today. We discussed that novel about the lighthouse keeper. Everyone had different opinions which made for a good conversation. I should read more often.",
    "Made banana bread this afternoon. The whole house smells amazing. I put some walnuts in like my mother used to. I will save a slice for when the nurse comes tomorrow morning.",
    "Slept quite poorly again. Keep waking at around three in the morning and then cannot get back to sleep. Feel groggy and slow today. Not much energy to do things. Just sat and watched television.",
    "My friend Dorothy came for tea this afternoon. We had not seen each other since Christmas. She looks well. We talked for nearly two hours. It was so good to have company in the house.",
    "Feeling quite low today. Not sure what brought it on. The house feels very quiet. I keep thinking about things I should have done differently. Hope tomorrow is a better day for me.",
    "Went to the supermarket this morning. Bumped into my neighbour Patricia at the checkout. We chatted for a while about the new road works on the high street. Picked up some fresh flowers.",
    "Did some gentle stretching exercises this morning following that video Sarah showed me. My back felt much better afterwards. I should try to do it every morning if I remember to.",
    "Feeling much brighter today. The sun is out and I have energy. Made a proper cooked breakfast and did some tidying. Put on some music while I cleaned. Really felt like myself again.",
    "Had a bit of a fall in the garden this morning, just tripped on the step. Not hurt, just a bit shaken. Sat down for a while. I need to be more careful. Maybe I should get that step fixed.",
    "Spoke to Michael about possibly going to visit the coast in the summer. He thinks it is a good idea. We used to go every year when the children were small. Would be nice to see the sea again.",
    "Not feeling well today, think I might be coming down with a cold. My throat is scratchy and I feel quite tired. Took some paracetamol and had a hot drink. Just resting and watching television.",
    "Finished the puzzle I have been working on for two weeks, the one with the flowers. One thousand pieces. Felt very satisfied when I put the last piece in. Might start the castle one next.",
    "Had a lovely dream about John last night. We were dancing, like we used to at the village hall. Woke up feeling sad but also warm, if that makes sense. I still miss him every single day.",
    "Feeling more like myself today. Had a proper breakfast and did some watering in the garden. The sweet peas are coming along beautifully. Might cut some for the vase on the kitchen table.",
]

# ── Sessions (days_ago, hour, transcript_idx) ─────────────────────────────────

SESSIONS = [
    (21, 10, 0),  (20, 14, 1),  (19, 9,  2),  (18, 11, 3),  (17, 15, 4),
    (16, 10, 5),  (15, 9,  6),  (14, 16, 7),  (13, 11, 8),  (12, 14, 9),
    (11, 10, 10), (10, 9,  11), (9,  15, 12), (8,  10, 13), (7,  14, 14),
    (6,  10, 15), (5,  9,  16), (4,  14, 17), (3,  10, 18), (2,  15, 19),
    (2,  16, 20), (1,  10, 21), (1,  14, 22), (0,  10, 23), (0,  14, 24),
]

# ── Pre-written memories (one set per transcript) ─────────────────────────────

MOCK_MEMORIES = {
    0: [
        {"type": "event", "content": "Emily went to the park with her daughter Sarah and fed the ducks", "valence": None, "keywords": ["park", "Sarah", "ducks"]},
        {"type": "fact",  "content": "Emily has a daughter named Sarah", "valence": None, "keywords": ["Sarah", "daughter"]},
        {"type": "mood",  "content": "Emily felt very relaxed and happy after the park outing with Sarah", "valence": 0.75, "keywords": ["relaxed", "happy", "lovely"]},
    ],
    1: [
        {"type": "mood",  "content": "Emily has been sleeping poorly and waking multiple times during the night", "valence": -0.45, "keywords": ["tired", "sleep", "waking"]},
        {"type": "fact",  "content": "Emily believes the heat may be disrupting her sleep", "valence": None, "keywords": ["heat", "sleep", "chamomile"]},
    ],
    2: [
        {"type": "event", "content": "Emily had a long phone call with her sister Margaret about her garden", "valence": None, "keywords": ["phone call", "Margaret", "garden"]},
        {"type": "fact",  "content": "Emily has a sister named Margaret who grows tomatoes", "valence": None, "keywords": ["Margaret", "sister", "tomatoes"]},
        {"type": "mood",  "content": "Emily felt joyful and uplifted catching up with her sister Margaret", "valence": 0.85, "keywords": ["wonderful", "laughed", "lovely"]},
    ],
    3: [
        {"type": "event", "content": "Emily visited the doctor and learned her blood pressure is slightly elevated", "valence": None, "keywords": ["doctor", "blood pressure", "appointment"]},
        {"type": "fact",  "content": "Emily has slightly elevated blood pressure and must reduce salt and keep walking", "valence": None, "keywords": ["blood pressure", "salt", "health"]},
        {"type": "mood",  "content": "Emily felt calm and reasonably okay about the doctor's health news", "valence": 0.15, "keywords": ["alright", "okay", "not concerning"]},
    ],
    4: [
        {"type": "event", "content": "Emily watched a nature documentary about penguins", "valence": None, "keywords": ["documentary", "penguins", "television"]},
        {"type": "fact",  "content": "Emily's friend Michael is interested in watching the penguin documentary", "valence": None, "keywords": ["Michael", "documentary", "penguins"]},
        {"type": "mood",  "content": "Emily felt fascinated and engaged watching the penguin documentary", "valence": 0.65, "keywords": ["fascinating", "fascinating", "engaged"]},
    ],
    5: [
        {"type": "event", "content": "Emily cooked a new chicken soup recipe with ginger", "valence": None, "keywords": ["chicken soup", "ginger", "cooking"]},
        {"type": "fact",  "content": "Emily plans to make chicken soup again for the grandchildren's visit", "valence": None, "keywords": ["grandchildren", "visit", "soup"]},
        {"type": "mood",  "content": "Emily felt pleased and satisfied cooking in her kitchen", "valence": 0.6, "keywords": ["good", "wonderful", "satisfied"]},
    ],
    6: [
        {"type": "mood",  "content": "Emily felt deeply nostalgic and sad thinking about her late mother", "valence": -0.5, "keywords": ["mother", "miss", "nostalgic", "sad"]},
        {"type": "fact",  "content": "Emily's mother would have turned 83 this week", "valence": None, "keywords": ["mother", "birthday", "83"]},
        {"type": "fact",  "content": "Emily and her mother had a Sunday baking tradition together", "valence": None, "keywords": ["baking", "Sunday", "mother", "tradition"]},
    ],
    7: [
        {"type": "event", "content": "Emily walked 40 minutes along the river path and saw a heron", "valence": None, "keywords": ["walk", "river", "heron", "exercise"]},
        {"type": "mood",  "content": "Emily's knee was stiff at first but improved as she warmed up during the walk", "valence": 0.2, "keywords": ["knee", "stiff", "better", "walk"]},
    ],
    8: [
        {"type": "event", "content": "Emily's grandson Tommy called on video and read aloud from his book", "valence": None, "keywords": ["Tommy", "video call", "reading", "grandson"]},
        {"type": "fact",  "content": "Emily's grandson Tommy is learning to read", "valence": None, "keywords": ["Tommy", "reading", "learning", "grandson"]},
        {"type": "mood",  "content": "Emily felt extremely proud watching her grandson Tommy read to her", "valence": 0.9, "keywords": ["proud", "remarkable", "joy"]},
    ],
    9: [
        {"type": "event", "content": "Emily sorted through old photographs from a family holiday in Portugal", "valence": None, "keywords": ["photographs", "Portugal", "holiday", "memories"]},
        {"type": "fact",  "content": "Emily's family holidayed in Portugal around 1987", "valence": None, "keywords": ["Portugal", "1987", "holiday", "family"]},
        {"type": "mood",  "content": "Emily felt pleasantly nostalgic looking through the old family photographs", "valence": 0.4, "keywords": ["memories", "nostalgic", "good memories"]},
    ],
    10: [
        {"type": "mood",  "content": "Emily experienced unexplained morning anxiety and a general sense of unease", "valence": -0.55, "keywords": ["anxious", "unease", "worried", "morning"]},
        {"type": "event", "content": "Emily used breathing exercises and tea in the garden to manage her anxiety", "valence": None, "keywords": ["breathing exercises", "tea", "garden", "calm"]},
    ],
    11: [
        {"type": "event", "content": "Emily attended book club and discussed a novel about a lighthouse keeper", "valence": None, "keywords": ["book club", "lighthouse", "novel", "discussion"]},
        {"type": "mood",  "content": "Emily felt engaged and intellectually stimulated by the book club debate", "valence": 0.65, "keywords": ["lovely", "good conversation", "opinions"]},
    ],
    12: [
        {"type": "event", "content": "Emily baked banana bread with walnuts following her mother's recipe", "valence": None, "keywords": ["banana bread", "walnuts", "baking", "recipe"]},
        {"type": "fact",  "content": "Emily's mother used to add walnuts to banana bread — a family tradition", "valence": None, "keywords": ["mother", "walnuts", "tradition", "baking"]},
        {"type": "mood",  "content": "Emily felt warm and contented baking at home", "valence": 0.7, "keywords": ["amazing", "smells", "content", "warm"]},
    ],
    13: [
        {"type": "mood",  "content": "Emily slept very poorly, waking at 3am and unable to return to sleep", "valence": -0.7, "keywords": ["poor sleep", "3am", "waking", "insomnia"]},
        {"type": "mood",  "content": "Emily felt groggy with very low energy and motivation all day", "valence": -0.65, "keywords": ["groggy", "slow", "no energy", "tired"]},
    ],
    14: [
        {"type": "event", "content": "Emily's friend Dorothy visited for tea for the first time since Christmas", "valence": None, "keywords": ["Dorothy", "tea", "visit", "friend"]},
        {"type": "fact",  "content": "Emily and her close friend Dorothy had not seen each other since Christmas", "valence": None, "keywords": ["Dorothy", "friend", "Christmas"]},
        {"type": "mood",  "content": "Emily felt uplifted and happy having a friend visit the house", "valence": 0.8, "keywords": ["company", "wonderful", "uplifted", "happy"]},
    ],
    15: [
        {"type": "mood",  "content": "Emily felt persistently low and sad without any identifiable reason", "valence": -0.75, "keywords": ["low", "sad", "unexplained", "down"]},
        {"type": "mood",  "content": "Emily felt lonely as the house seemed unusually quiet and empty", "valence": -0.65, "keywords": ["quiet", "lonely", "house", "alone"]},
    ],
    16: [
        {"type": "event", "content": "Emily went to the supermarket and bought fresh flowers", "valence": None, "keywords": ["supermarket", "shopping", "flowers"]},
        {"type": "event", "content": "Emily bumped into her neighbour Patricia and chatted about road works", "valence": None, "keywords": ["Patricia", "neighbour", "road works", "supermarket"]},
    ],
    17: [
        {"type": "event", "content": "Emily did gentle stretching exercises from a video her daughter Sarah shared", "valence": None, "keywords": ["stretching", "exercises", "Sarah", "video"]},
        {"type": "mood",  "content": "Emily's back felt significantly better after the morning stretching routine", "valence": 0.5, "keywords": ["back", "better", "stretching", "relief"]},
    ],
    18: [
        {"type": "mood",  "content": "Emily felt energetic and fully like herself — a noticeably better day", "valence": 0.85, "keywords": ["bright", "energy", "myself", "good day"]},
        {"type": "event", "content": "Emily cleaned the house while playing music, feeling well and active", "valence": None, "keywords": ["cleaning", "music", "housework", "active"]},
    ],
    19: [
        {"type": "event", "content": "Emily tripped on the garden step and fell, though she was not seriously hurt", "valence": None, "keywords": ["fall", "garden step", "tripped", "accident"]},
        {"type": "mood",  "content": "Emily felt shaken and unsettled after the fall in the garden", "valence": -0.6, "keywords": ["shaken", "careful", "unsettled", "fall"]},
        {"type": "fact",  "content": "The garden step where Emily fell needs to be repaired for safety", "valence": None, "keywords": ["garden step", "repair", "safety"]},
    ],
    20: [
        {"type": "event", "content": "Emily and Michael discussed a possible summer trip to the coast", "valence": None, "keywords": ["Michael", "coast", "summer", "trip"]},
        {"type": "fact",  "content": "Emily's family used to visit the coast every year when the children were young", "valence": None, "keywords": ["coast", "family tradition", "children", "sea"]},
        {"type": "mood",  "content": "Emily felt hopeful and nostalgic thinking about revisiting the sea", "valence": 0.45, "keywords": ["hopeful", "nice", "sea", "nostalgic"]},
    ],
    21: [
        {"type": "mood",  "content": "Emily felt unwell and believed she was coming down with a cold", "valence": -0.5, "keywords": ["unwell", "cold", "ill", "poorly"]},
        {"type": "event", "content": "Emily took paracetamol and rested at home with a hot drink", "valence": None, "keywords": ["paracetamol", "resting", "hot drink", "unwell"]},
    ],
    22: [
        {"type": "event", "content": "Emily completed a 1000-piece flower jigsaw puzzle after two weeks of work", "valence": None, "keywords": ["puzzle", "1000 pieces", "flowers", "completed"]},
        {"type": "mood",  "content": "Emily felt very satisfied and accomplished finishing the jigsaw puzzle", "valence": 0.8, "keywords": ["satisfied", "accomplished", "last piece"]},
    ],
    23: [
        {"type": "event", "content": "Emily dreamed about dancing with her late husband John at the village hall", "valence": None, "keywords": ["dream", "John", "dancing", "village hall"]},
        {"type": "fact",  "content": "Emily and her late husband John used to dance together at the village hall", "valence": None, "keywords": ["John", "dancing", "village hall", "husband"]},
        {"type": "mood",  "content": "Emily woke feeling bittersweet — sad but warmly comforted by the dream of John", "valence": -0.2, "keywords": ["sad", "warm", "bittersweet", "miss John"]},
    ],
    24: [
        {"type": "mood",  "content": "Emily felt recovered and more like herself again today", "valence": 0.75, "keywords": ["better", "myself", "recovered", "good"]},
        {"type": "event", "content": "Emily watered the garden and cut sweet peas to put in a kitchen vase", "valence": None, "keywords": ["garden", "sweet peas", "flowers", "kitchen"]},
    ],
}


# ── Snapshot generation ───────────────────────────────────────────────────────

def make_timestamp(days_ago, hour, minute, second=0):
    base = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return base.replace(hour=hour, minute=minute, second=second, microsecond=random.randint(0, 999999))


def session_metrics(days_ago, transcript_idx):
    base_sr, base_ar = 148.0, 162.0
    base_ph, base_pa = 0.78, 0.52
    base_f0, base_ji, base_sh = 198.0, 0.024, 1.05
    decline = max(0.0, (8 - days_ago) / 8)
    n = lambda s: random.gauss(0, s)

    low_mood = {13, 15, 21}
    pos_mood = {1, 2, 8, 9, 18, 24}
    mood_off = -0.35 if transcript_idx in low_mood else (0.25 if transcript_idx in pos_mood else 0.0)

    speech_rate  = max(80,  base_sr * (1 - decline * 0.18) + n(6))
    articulation = max(90,  base_ar * (1 - decline * 0.12) + n(5))
    phonation    = min(0.99, max(0.3, base_ph * (1 - decline * 0.08) + n(0.03)))
    pause        = max(0.1,  base_pa * (1 + decline * 0.45) + n(0.05))
    f0           = max(80,   base_f0 * (1 - decline * 0.07) + n(8))
    jitter       = max(0.005, base_ji * (1 + decline * 0.5) + n(0.003))
    shimmer      = max(0.3,  base_sh * (1 + decline * 0.4) + n(0.08))

    text   = TRANSCRIPTS[transcript_idx]
    words  = text.lower().split()
    ttr    = len(set(words)) / len(words) if words else 0.45

    pos_w = {'lovely','wonderful','good','happy','great','nice','beautiful','well','bright','proud','warm','relaxed','satisfied','fascinating'}
    neg_w = {'tired','anxious','sad','miss','low','poorly','shaken','groggy','unease','hurt','worried','slow','waking'}
    pos = sum(1 for w in words if w in pos_w)
    neg = sum(1 for w in words if w in neg_w)
    emotion = max(-1.0, min(1.0, ((pos - neg) / len(words)) * 3 + mood_off + n(0.05)))

    word_count   = len(words)
    duration_sec = word_count / (speech_rate / 60) if speech_rate > 0 else 30

    return {
        "temporal": {
            "speech_rate_wpm": round(speech_rate, 3),
            "articulation_rate_wpm": round(articulation, 3),
            "phonation_to_time_ratio": round(phonation, 4),
            "mean_pause_duration_sec": round(pause, 3),
            "word_count": word_count,
            "duration_sec": round(duration_sec, 2),
        },
        "lexical": {
            "emotion_score": round(emotion, 4),
            "self_pronoun_ratio": round(max(0, sum(1 for w in words if w in {"i","me","my","mine","myself"}) / len(words)), 4),
            "type_token_ratio": round(ttr, 4),
        },
        "prosody": {
            "f0_mean_hz": round(f0, 4),
            "jitter_local": round(jitter, 6),
            "shimmer_local_db": round(shimmer, 6),
        },
        "spectral": {},
    }


def make_snapshot(days_ago, hour, transcript_idx):
    ts    = make_timestamp(days_ago, hour, random.randint(0, 59))
    fname = ts.strftime("%Y%m%dT%H%M%S") + f"_{random.randint(100000, 999999)}.json"
    return fname, ts, {
        "event": {"time": ts.isoformat(), "day": ts.strftime("%Y-%m-%d")},
        "source_file": f"session_{transcript_idx:03d}.wav",
        "transcript": TRANSCRIPTS[transcript_idx],
        "metrics": session_metrics(days_ago, transcript_idx),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    AGGREGATES_DIR.mkdir(parents=True, exist_ok=True)

    # Clear existing snapshots
    for f in SNAPSHOTS_DIR.glob("*.json"):
        f.unlink()

    print(f"Generating {len(SESSIONS)} mock sessions…")
    session_times = {}
    for days_ago, hour, tidx in SESSIONS:
        fname, ts, snapshot = make_snapshot(days_ago, hour, tidx)
        (SNAPSHOTS_DIR / fname).write_text(json.dumps(snapshot, indent=2))
        session_times[tidx] = (ts, snapshot["event"]["time"], snapshot["event"]["day"])
        print(f"  {fname[:20]}… [{TRANSCRIPTS[tidx][:55]}…]")

    # ── Regenerate aggregates ──────────────────────────────────────────────
    print("\nRunning aggregator…")
    from localhost_demo.services.aggregator import compute_aggregate, _read_snapshots
    from localhost_demo.services.contracts import write_json, append_jsonl

    (AGGREGATES_DIR / "history.jsonl").write_text("")

    snapshots = _read_snapshots(SNAPSHOTS_DIR)

    # Build daily emotion cache using the same keyword formula as session_metrics
    # (avoids a heavy HuggingFace model download during mock generation).
    pos_w = {'lovely','wonderful','good','happy','great','nice','beautiful','well','bright',
             'proud','warm','relaxed','satisfied','fascinating'}
    neg_w = {'tired','anxious','sad','miss','low','poorly','shaken','groggy','unease',
             'hurt','worried','slow','waking'}
    by_day: dict[str, list] = {}
    for snap in snapshots:
        day = (snap.get("event") or {}).get("day", "")
        if day:
            by_day.setdefault(day, []).append(snap)
    daily_emotion: dict = {}
    for day, day_snaps in by_day.items():
        scores = []
        for snap in day_snaps:
            words = (snap.get("transcript") or "").lower().split()
            if not words:
                continue
            pos = sum(1 for w in words if w in pos_w)
            neg = sum(1 for w in words if w in neg_w)
            scores.append(max(-1.0, min(1.0, (pos - neg) / len(words) * 3)))
        emo = round(sum(scores) / len(scores), 6) if scores else 0.0
        daily_emotion[day] = {"emotion_score": emo, "snapshot_count": len(day_snaps)}
    DAILY_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DAILY_CACHE_PATH.write_text(json.dumps(daily_emotion, indent=2, sort_keys=True))
    aggregate      = compute_aggregate(
        snapshots,
        max_transcript_items=25,
        segment_minutes=1,
        current_window_minutes=60,
        baseline_percent=0.25,
        daily_emotion_cache=daily_emotion,
    )
    write_json(AGGREGATES_DIR / "current.json", aggregate)
    append_jsonl(AGGREGATES_DIR / "history.jsonl", aggregate)

    # ── Generate memories ──────────────────────────────────────────────────
    print("\nGenerating typed memories…")
    memories = []
    for tidx, (ts, event_time, day) in sorted(session_times.items()):
        for raw in MOCK_MEMORIES.get(tidx, []):
            memories.append({
                "id": f"m_{uuid.uuid4().hex[:10]}",
                "type": raw["type"],
                "content": raw["content"],
                "valence": raw.get("valence"),
                "keywords": raw.get("keywords", []),
                "date": day,
                "source_event_time": event_time,
                "source_text": TRANSCRIPTS[tidx],
            })

    from localhost_demo.services.memory_service import MemoryService
    svc = MemoryService(SNAPSHOTS_DIR, AGGREGATES_DIR)
    svc.save_memories(memories)

    by_type = {t: sum(1 for m in memories if m["type"] == t) for t in ("event", "fact", "mood")}
    print(f"\nDone!")
    print(f"  Snapshots: {len(snapshots)}")
    print(f"  Memories:  {len(memories)} total — {by_type}")
    print(f"  Alerts:    {[a['metric'] for a in aggregate['alerts']['items'] if a['status'] != 'ok'] or ['none']}")

    # Verify graph
    graph = svc.get_memories()["graph"]
    print(f"  Graph:     {len(graph['nodes'])} nodes, {len(graph['links'])} edges")


if __name__ == "__main__":
    main()

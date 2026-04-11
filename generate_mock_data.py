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
    # 0 — 21 days ago, morning
    "Went for my walk this morning before breakfast. The whole lane was lined with cow parsley, it looked almost like snow. And then I spotted a red kite circling above the field, very high up. I stood and watched it for a good few minutes. Felt very peaceful and rather lucky to see that. Had a boiled egg and read the paper when I got home. A good start to the day.",
    # 1 — 20 days ago, afternoon
    "Stayed indoors most of the day because of the rain, which suited me fine. Spent the afternoon reading and then had a bit of a cry, which actually felt quite good in a way. I found an old postcard tucked inside my book, from John, written on a work trip to Edinburgh. Just silly little things on it, something about the weather and a pub he liked. But I kept reading it over and over. Went to bed early.",
    # 2 — 19 days ago, morning
    "Had such a lovely phone call with Sarah this morning, we chatted for nearly an hour. She told me that Tommy has been given the lead part in his school play. He is going to be a lighthouse keeper which is quite funny. She said he has been rehearsing his lines around the house all week. I had my coffee while we talked and felt so happy and proud just hearing about it. Cannot wait to see him on stage.",
    # 3 — 18 days ago, morning
    "Doctor's appointment first thing. He says my cholesterol is a little on the high side and wants to keep an eye on it. Suggested I cut back on butter and cheese, which I am not at all happy about if I am honest. On the better side he said my blood pressure has actually improved since last time, which was encouraging. Picked up my prescription and walked home. Had soup for lunch and watched the afternoon news. Fairly ordinary rest of the day.",
    # 4 — 17 days ago, afternoon
    "I made John's lamb stew today. I have not cooked it since before he died, nearly two years now. I was not sure I would remember the recipe but my hands just seemed to know what to do. The whole kitchen smelled exactly like it used to on a Sunday. I sat and ate a bowl of it on my own and felt his absence very strongly. It was painful but also strangely comforting. I think I will make it again. It felt like keeping something alive.",
    # 5 — 16 days ago, ordinary day
    "Quite a nice ordinary day today. Had porridge and listened to the radio. Did some weeding in the front garden before it got too hot. Popped to the post office to send a birthday card to my cousin Patricia and bumped into Mr Henderson from the village. We had a nice chat about nothing in particular. Came home, had a cheese sandwich for lunch, watched Countdown in the afternoon. All in all a perfectly fine quiet day.",
    # 6 — 15 days ago, evening
    "Book club this evening was quite lively. We were discussing a memoir about a woman who walks across Iceland alone. There was a real debate about whether she was being self-indulgent or brave. I said I thought she was both and everyone laughed. Celia brought her lemon drizzle cake which was absolutely delicious, I had two slices. Walked home in the evening light feeling very stimulated. Glad I made the effort to go.",
    # 7 — 14 days ago, afternoon
    "Tommy's school play this afternoon. I could not be more proud if I tried. He stood up on that little stage and said every single line perfectly and loudly. When he spotted me in the audience he gave a tiny wave and I genuinely thought my heart might burst. Sarah and I took him for ice cream afterwards and he had two scoops of chocolate. He told us all about the backstage nerves on the way home. What a wonderful afternoon.",
    # 8 — 13 days ago, bad night
    "A very difficult night. Woke at around half two and could not get back to sleep at all. My mind was racing, going over all sorts of things. Whether the boiler needs a service, whether I said something odd to Sarah last week. Nothing actually serious but at three in the morning everything feels enormous. Got up and made tea and watched an old film until it was light. Feel absolutely dreadful today, slow and foggy. Hard to concentrate on anything.",
    # 9 — 12 days ago, afternoon
    "I finally went through the spare room today. John's things have been sitting in boxes in there since we cleared his study. I did not expect it to take all afternoon but it did. Found his bird-watching notebook, all his lists in his handwriting. I sat down on the floor and just held it for quite a long time. Kept some things, put some in bags for the charity shop. I feel wrung out and emotional but also, strangely, just a tiny bit lighter.",
    # 10 — 11 days ago, afternoon
    "Dorothy and I had lunch at that new little café on the high street, the one that does the open sandwiches. I had smoked salmon and it was very good. We talked for nearly two and a half hours. She is having some difficulty with her daughter-in-law, nothing serious but you could tell she needed to talk and I mostly just listened. It is nice to feel useful. Walked home feeling very fond of her and glad we made the effort.",
    # 11 — 10 days ago, morning
    "Had a strange moment this morning that unsettled me quite a lot. I was trying to tell the radio presenter to be quiet and I could not think of the word for the thing you use to open wine. I knew exactly what it was, I could picture it sitting in the kitchen drawer, but the word would not come. It took me nearly ten minutes. Corkscrew. Obviously corkscrew. I am sure it happens to everyone but it gave me a real fright. I did not mention it to anyone. Had a normal afternoon watching television.",
    # 12 — 9 days ago, afternoon
    "A beautiful day so I spent most of it in the garden. Planted the new lavender along the back fence and I think it will look lovely come summer. Got quite sweaty doing it and my knees were not very happy, but it was worth it. Found an old ceramic pot buried under the hedge, must have been put there by John years ago. Cleaned it up nicely. Might put herbs in it. Sat outside with a cold glass of water when I had finished. Felt very satisfied.",
    # 13 — 8 days ago, morning
    "Long video call with Margaret today and she gave me quite a fright at the beginning because she looked very worried. Turns out her husband Robert had chest pains last week and spent two nights in hospital. He is fine now, they think it was stress related rather than his heart. But still, you do not expect that sort of news. We talked for a long time. I feel so far away from her. We agreed we absolutely must arrange a visit before the end of the summer.",
    # 14 — 7 days ago, full day
    "My hip has been really painful today, worse than it has been for a while. Think it might be the weather turning. Did very little, watched television most of the day which is not like me at all. Made myself a proper dinner at least, chicken and vegetables. Took a painkiller at bedtime. I hate feeling like this, it makes me feel old and useless and frustrated. Really hope it eases off tomorrow.",
    # 15 — 6 days ago, morning
    "I telephoned Brenda today, which I have been meaning to do for months. We were friends all through school, then lost touch for a while, found each other again a few years ago. She is in Cornwall now, has been for years. We talked for over an hour. She told me she and her husband walk every single morning without fail. We made quite a firm plan to visit each other this summer. I felt very warm after hanging up. Some friendships just pick right back up.",
    # 16 — 5 days ago, evening
    "A quiet day at home mostly, pottered about and did some ironing. In the evening I watched a wonderful programme about Patagonia, all about the wildlife. The condors were extraordinary, these enormous birds just riding the thermals for hours. Made me think about the red kite I saw the other week. I would love to travel again, even somewhere in Britain I have never been. Had a cup of chamomile and went to bed feeling quite content.",
    # 17 — 4 days ago, afternoon
    "Sarah brought Tommy round for the afternoon, which was just wonderful. He helped me water the plants in the garden, which mostly meant he soaked himself with the hose. We had tea and I made a Victoria sponge and Tommy ate three slices without any embarrassment at all. He told me he wants to be an astronaut now, which has changed from last month when it was a dinosaur. Sarah looked a bit tired but happy. I felt so full when they left. The good kind of full.",
    # 18 — 3 days ago, overnight and next day
    "Another wretched night. Woke at two and then again at four and could not get back to sleep either time. My mind just will not settle lately. Felt slow and foggy all day and could not concentrate on my book at all. Had a nap after lunch which helped a little. I really do worry when the bad nights cluster together like this. Made a note to mention it to the doctor at the next appointment. Had beans on toast for dinner because I could not face cooking properly.",
    # 19 — 2 days ago, morning
    "Woke up feeling much better today, which was such a relief. Made a proper cooked breakfast, eggs and tomatoes. Then got out my watercolours, which I have not touched in months. Did a little sketch of the view from the kitchen window, nothing very accomplished but I enjoyed the doing of it. Listened to Radio Four in the afternoon. Felt genuinely like myself again. It is funny how quickly things can shift when you get a decent night.",
    # 20 — 2 days ago, afternoon
    "Had a bit of a turn this afternoon. Stood up from the armchair a bit too quickly and everything went dark and swimmy for a moment. I held onto the doorframe and it passed after a few seconds. I know the doctor said it is just blood pressure when you stand too fast but it still gives you a real fright every time it happens. Sat back down for a while. Told myself I will mention it at my next appointment. Did not want to bother anyone.",
    # 21 — 1 day ago, morning
    "Michael drove me to the garden centre this morning, which was very kind of him. I bought two more lavender plants and some trailing geraniums for the window boxes. He pushed the trolley and carried everything to the car. We stopped for coffee and a scone on the way home and sat by the window. The geraniums are already in the boxes and they look very cheerful. Really nice to get out and have some company for a few hours.",
    # 22 — 1 day ago, afternoon
    "A very peaceful afternoon. Put on some old records, Ella Fitzgerald first and then Frank Sinatra, and sat and knitted. I am making a cardigan for Tommy in navy blue, quite a complicated yoke pattern. The music and the knitting together with the sun coming through the window felt very settling. Almost like a kind of meditation I suppose. Finished two rows of the yoke. Had a small glass of sherry before supper which felt like a proper little luxury.",
    # 23 — today, early morning
    "Woke very early this morning, just after five, and instead of lying there I got up and took my tea out into the garden. It was that grey-gold light you only get at that hour. Completely quiet except for the birds. Sat for almost an hour just watching everything slowly come to life. A fox came through the gap in the hedge bold as anything and looked straight at me, neither of us moving. Did not feel lonely at all. Felt quite the opposite.",
    # 24 — today, midday
    "Sarah and Michael are both coming for Sunday lunch today and I have Tommy as well. I have the leg of lamb in the oven with rosemary, roast potatoes, green beans. The house smells absolutely wonderful. I love having a full table. I will be tired afterwards of course but it is the good kind of tired. This is exactly the kind of Sunday I like best and I feel completely ready for it.",
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
        {"type": "event", "content": "Spotted a red kite circling above the field on morning walk", "valence": None, "keywords": ["red kite", "walk", "bird", "field"]},
        {"type": "event", "content": "Had a boiled egg and read the paper after the walk", "valence": None, "keywords": ["breakfast", "boiled egg", "paper", "morning"]},
        {"type": "mood",  "content": "Emily felt peaceful and lucky seeing the red kite", "valence": 0.8, "keywords": ["peaceful", "lucky", "morning", "nature"]},
        {"type": "fact",  "content": "Emily enjoys early morning walks before breakfast", "valence": None, "keywords": ["walks", "morning", "routine", "exercise"]},
    ],
    1: [
        {"type": "event", "content": "Found an old postcard from John tucked in a book", "valence": None, "keywords": ["postcard", "John", "Edinburgh", "book"]},
        {"type": "event", "content": "Spent a rainy afternoon indoors reading and went to bed early", "valence": None, "keywords": ["reading", "rain", "indoors", "afternoon"]},
        {"type": "mood",  "content": "Emily cried reading John's old postcard — sad but cathartic", "valence": -0.3, "keywords": ["cry", "John", "miss", "postcard"]},
        {"type": "fact",  "content": "John wrote postcards to Emily when he was away on work trips", "valence": None, "keywords": ["John", "postcards", "Edinburgh", "work trips"]},
    ],
    2: [
        {"type": "event", "content": "Tommy got the lead role in his school play as a lighthouse keeper", "valence": None, "keywords": ["Tommy", "school play", "lighthouse keeper", "lead role"]},
        {"type": "event", "content": "Long phone call with Sarah over morning coffee — chatted for nearly an hour", "valence": None, "keywords": ["Sarah", "phone call", "coffee", "morning"]},
        {"type": "mood",  "content": "Emily felt excited and proud hearing about Tommy's school play role", "valence": 0.85, "keywords": ["excited", "proud", "happy", "Tommy"]},
        {"type": "fact",  "content": "Tommy has the lead part in his school play as a lighthouse keeper", "valence": None, "keywords": ["Tommy", "school play", "lighthouse keeper", "lead"]},
    ],
    3: [
        {"type": "event", "content": "Doctor said cholesterol is slightly high and needs monitoring", "valence": None, "keywords": ["doctor", "cholesterol", "appointment", "health"]},
        {"type": "event", "content": "Had soup for lunch and watched the afternoon news", "valence": None, "keywords": ["soup", "lunch", "news", "afternoon"]},
        {"type": "mood",  "content": "Emily felt encouraged by improved blood pressure but unhappy about the diet advice", "valence": 0.2, "keywords": ["encouraged", "blood pressure", "cholesterol", "diet"]},
        {"type": "fact",  "content": "Emily's cholesterol is elevated — doctor advised cutting butter and cheese", "valence": None, "keywords": ["cholesterol", "butter", "cheese", "diet"]},
        {"type": "fact",  "content": "Emily's blood pressure has improved since her last appointment", "valence": None, "keywords": ["blood pressure", "improved", "doctor", "health"]},
    ],
    4: [
        {"type": "event", "content": "Cooked John's lamb stew for the first time in nearly two years", "valence": None, "keywords": ["lamb stew", "John", "cooking", "recipe"]},
        {"type": "mood",  "content": "Emily felt John's absence strongly cooking his recipe but also comforted", "valence": -0.15, "keywords": ["miss John", "absence", "comfort", "bittersweet"]},
        {"type": "fact",  "content": "Lamb stew was John's recipe and they always had it on Sundays", "valence": None, "keywords": ["John", "lamb stew", "Sundays", "recipe", "tradition"]},
        {"type": "fact",  "content": "John passed away nearly two years ago", "valence": None, "keywords": ["John", "passed away", "two years", "grief"]},
    ],
    5: [
        {"type": "event", "content": "Had porridge and listened to the radio for breakfast", "valence": None, "keywords": ["porridge", "radio", "breakfast", "morning routine"]},
        {"type": "event", "content": "Did weeding in the front garden in the morning before the heat", "valence": None, "keywords": ["weeding", "garden", "morning", "outdoors"]},
        {"type": "event", "content": "Bumped into Mr Henderson from the village at the post office", "valence": None, "keywords": ["Mr Henderson", "post office", "village", "chat"]},
        {"type": "event", "content": "Watched Countdown in the afternoon with a cheese sandwich", "valence": None, "keywords": ["Countdown", "TV", "afternoon", "sandwich"]},
        {"type": "mood",  "content": "Emily felt quietly content with an ordinary pleasant day", "valence": 0.55, "keywords": ["content", "pleasant", "ordinary", "quiet day"]},
    ],
    6: [
        {"type": "event", "content": "Book club debated a memoir about a woman walking across Iceland alone", "valence": None, "keywords": ["book club", "Iceland", "memoir", "debate"]},
        {"type": "event", "content": "Celia brought lemon drizzle cake to book club — Emily had two slices", "valence": None, "keywords": ["Celia", "lemon drizzle", "cake", "book club"]},
        {"type": "mood",  "content": "Emily felt stimulated and glad she made the effort to go to book club", "valence": 0.75, "keywords": ["stimulated", "glad", "engaged", "lively"]},
        {"type": "fact",  "content": "Celia is a book club member known for her lemon drizzle cake", "valence": None, "keywords": ["Celia", "book club", "lemon drizzle", "friend"]},
    ],
    7: [
        {"type": "event", "content": "Watched Tommy perform the lead role in his school play", "valence": None, "keywords": ["Tommy", "school play", "performance", "stage"]},
        {"type": "event", "content": "Took Tommy for two scoops of chocolate ice cream after the play", "valence": None, "keywords": ["Tommy", "ice cream", "chocolate", "after show"]},
        {"type": "mood",  "content": "Emily's heart burst with pride when Tommy waved to her from the stage", "valence": 0.95, "keywords": ["proud", "heart burst", "Tommy", "wave"]},
        {"type": "fact",  "content": "Tommy spotted Emily in the audience and gave her a little wave mid-performance", "valence": None, "keywords": ["Tommy", "wave", "audience", "proud moment"]},
    ],
    8: [
        {"type": "event", "content": "Woke at 2:30am with racing thoughts and could not get back to sleep", "valence": None, "keywords": ["insomnia", "2:30am", "woke", "racing thoughts"]},
        {"type": "event", "content": "Made tea and watched an old film alone until daylight", "valence": None, "keywords": ["tea", "old film", "sleepless", "night", "alone"]},
        {"type": "mood",  "content": "Emily felt absolutely dreadful after a sleepless night of racing thoughts", "valence": -0.75, "keywords": ["dreadful", "exhausted", "sleepless", "slow and foggy"]},
        {"type": "mood",  "content": "Emily worried she may have said something odd to Sarah last week", "valence": -0.5, "keywords": ["worry", "Sarah", "anxious", "night worries"]},
    ],
    9: [
        {"type": "event", "content": "Finally went through John's belongings in boxes in the spare room", "valence": None, "keywords": ["John", "spare room", "belongings", "sorting"]},
        {"type": "event", "content": "Found John's bird-watching notebook with all his handwritten lists", "valence": None, "keywords": ["John", "bird-watching", "notebook", "handwriting"]},
        {"type": "mood",  "content": "Emily sat on the floor holding John's notebook for a long time — overwhelmed", "valence": -0.4, "keywords": ["emotional", "John", "notebook", "grief"]},
        {"type": "mood",  "content": "After sorting John's things Emily felt wrung out but slightly lighter", "valence": 0.15, "keywords": ["lighter", "closure", "wrung out", "bittersweet"]},
        {"type": "fact",  "content": "John was a keen bird-watcher who kept detailed handwritten notebooks", "valence": None, "keywords": ["John", "bird-watching", "notebooks", "hobby"]},
    ],
    10: [
        {"type": "event", "content": "Had smoked salmon lunch at the new café on the high street with Dorothy", "valence": None, "keywords": ["Dorothy", "café", "smoked salmon", "lunch", "high street"]},
        {"type": "event", "content": "Talked with Dorothy for nearly two and a half hours over lunch", "valence": None, "keywords": ["Dorothy", "conversation", "lunch", "long chat"]},
        {"type": "mood",  "content": "Emily felt warm and useful after mostly listening to Dorothy's difficulties", "valence": 0.7, "keywords": ["warm", "useful", "fond", "friendship"]},
        {"type": "fact",  "content": "Dorothy is having difficulty with her daughter-in-law at the moment", "valence": None, "keywords": ["Dorothy", "daughter-in-law", "family", "difficulty"]},
    ],
    11: [
        {"type": "event", "content": "Could not recall the word 'corkscrew' for nearly ten minutes", "valence": None, "keywords": ["corkscrew", "word", "memory lapse", "forgot"]},
        {"type": "event", "content": "Had a normal afternoon watching television despite the earlier memory worry", "valence": None, "keywords": ["television", "afternoon", "watching TV", "routine"]},
        {"type": "mood",  "content": "The word-finding lapse frightened Emily — she told no one about it", "valence": -0.65, "keywords": ["frightened", "memory", "unsettled", "worried", "alone"]},
    ],
    12: [
        {"type": "event", "content": "Planted new lavender along the back garden fence", "valence": None, "keywords": ["lavender", "planting", "garden", "back fence"]},
        {"type": "event", "content": "Found an old ceramic pot buried under the hedge — must have been John's", "valence": None, "keywords": ["ceramic pot", "John", "hedge", "garden find"]},
        {"type": "mood",  "content": "Emily felt very satisfied after a productive and sweaty day gardening", "valence": 0.7, "keywords": ["satisfied", "productive", "garden", "content"]},
        {"type": "fact",  "content": "Emily is planting lavender along the back fence of her garden", "valence": None, "keywords": ["lavender", "garden", "back fence", "planting"]},
    ],
    13: [
        {"type": "event", "content": "Margaret's husband Robert spent two nights in hospital with chest pains", "valence": None, "keywords": ["Robert", "chest pains", "hospital", "health scare"]},
        {"type": "event", "content": "Emily and Margaret agreed to arrange a visit before end of summer", "valence": None, "keywords": ["visit", "Margaret", "summer", "plan"]},
        {"type": "mood",  "content": "Emily felt frightened and far away from Margaret during the health scare", "valence": -0.55, "keywords": ["frightened", "far away", "worried", "Margaret"]},
        {"type": "fact",  "content": "Margaret's husband Robert was hospitalised — doctors think stress, not his heart", "valence": None, "keywords": ["Robert", "chest pains", "stress", "hospital", "not heart attack"]},
        {"type": "fact",  "content": "Emily wants to visit her sister Margaret before the end of summer", "valence": None, "keywords": ["visit", "Margaret", "summer", "sisters"]},
    ],
    14: [
        {"type": "event", "content": "Spent most of the day resting on the sofa due to bad hip pain", "valence": None, "keywords": ["hip pain", "resting", "sofa", "television"]},
        {"type": "event", "content": "Made chicken and vegetables for dinner despite the pain", "valence": None, "keywords": ["dinner", "chicken", "vegetables", "cooking"]},
        {"type": "mood",  "content": "Emily felt frustrated and old — hip pain made her feel useless", "valence": -0.7, "keywords": ["frustrated", "old", "useless", "hip pain"]},
        {"type": "fact",  "content": "Emily has a recurring hip problem that worsens when the weather turns", "valence": None, "keywords": ["hip", "pain", "weather", "recurring", "health"]},
    ],
    15: [
        {"type": "event", "content": "Telephoned old school friend Brenda after months of meaning to call", "valence": None, "keywords": ["Brenda", "phone call", "school friend", "reconnecting"]},
        {"type": "event", "content": "Made a firm plan to visit Brenda in Cornwall this summer", "valence": None, "keywords": ["Brenda", "Cornwall", "visit", "summer plan"]},
        {"type": "mood",  "content": "Emily felt very warm after reconnecting with her old school friend Brenda", "valence": 0.8, "keywords": ["warm", "connected", "friendship", "school days"]},
        {"type": "fact",  "content": "Brenda is an old school friend now living in Cornwall with her husband", "valence": None, "keywords": ["Brenda", "Cornwall", "school friend", "old friend"]},
        {"type": "fact",  "content": "Brenda and her husband walk together every single morning without fail", "valence": None, "keywords": ["Brenda", "morning walks", "husband", "routine"]},
    ],
    16: [
        {"type": "event", "content": "Watched a programme about Patagonia featuring extraordinary condors", "valence": None, "keywords": ["Patagonia", "condors", "documentary", "wildlife"]},
        {"type": "event", "content": "Quiet day at home — pottered about, did some ironing, had chamomile tea", "valence": None, "keywords": ["ironing", "chamomile tea", "quiet day", "home"]},
        {"type": "mood",  "content": "Emily felt content and wistful — the condors made her want to travel again", "valence": 0.6, "keywords": ["content", "wistful", "travel", "nature"]},
        {"type": "fact",  "content": "Emily would love to travel again, even somewhere in Britain she has never been", "valence": None, "keywords": ["travel", "Britain", "wish", "adventure"]},
    ],
    17: [
        {"type": "event", "content": "Sarah brought Tommy round for the afternoon — had tea and Victoria sponge", "valence": None, "keywords": ["Sarah", "Tommy", "tea", "Victoria sponge", "afternoon visit"]},
        {"type": "event", "content": "Tommy helped water the garden and mostly soaked himself with the hose", "valence": None, "keywords": ["Tommy", "watering", "garden", "hose", "funny"]},
        {"type": "mood",  "content": "Emily felt wonderfully full in the good way after the family visit", "valence": 0.9, "keywords": ["wonderful", "full", "family", "happy", "warm"]},
        {"type": "fact",  "content": "Tommy now wants to be an astronaut — last month it was a dinosaur", "valence": None, "keywords": ["Tommy", "astronaut", "ambitions", "funny"]},
        {"type": "fact",  "content": "Emily made a Victoria sponge for the family visit and Tommy ate three slices", "valence": None, "keywords": ["Victoria sponge", "baking", "Tommy", "three slices"]},
    ],
    18: [
        {"type": "event", "content": "Woke at 2am and again at 4am — could not sleep either time", "valence": None, "keywords": ["poor sleep", "2am", "4am", "woke", "insomnia"]},
        {"type": "event", "content": "Had beans on toast for dinner — too tired to cook a proper meal", "valence": None, "keywords": ["beans on toast", "dinner", "too tired", "easy meal"]},
        {"type": "event", "content": "Made a note to mention the sleep pattern to the doctor", "valence": None, "keywords": ["doctor", "sleep", "note", "mention", "health"]},
        {"type": "mood",  "content": "Emily felt slow and foggy all day — worried about the clustering bad nights", "valence": -0.65, "keywords": ["foggy", "slow", "worried", "bad nights", "tired"]},
    ],
    19: [
        {"type": "event", "content": "Made a proper cooked breakfast — eggs and tomatoes", "valence": None, "keywords": ["eggs", "tomatoes", "breakfast", "cooked", "morning"]},
        {"type": "event", "content": "Got out the watercolours and painted the view from the kitchen window", "valence": None, "keywords": ["watercolours", "painting", "kitchen window", "art"]},
        {"type": "event", "content": "Listened to Radio Four in the afternoon", "valence": None, "keywords": ["Radio Four", "afternoon", "radio", "routine"]},
        {"type": "mood",  "content": "Emily felt genuinely like herself again after a bright good day", "valence": 0.8, "keywords": ["myself", "bright", "relief", "better", "good day"]},
        {"type": "fact",  "content": "Emily does watercolour painting as a hobby, though she had not touched them in months", "valence": None, "keywords": ["watercolours", "painting", "hobby", "art"]},
    ],
    20: [
        {"type": "event", "content": "Stood up from the armchair too quickly and had a dizzy spell", "valence": None, "keywords": ["dizzy", "stood up", "armchair", "blood pressure"]},
        {"type": "event", "content": "Held onto the doorframe until the dizziness passed in a few seconds", "valence": None, "keywords": ["doorframe", "dizzy", "held on", "passed"]},
        {"type": "mood",  "content": "The dizzy spell frightened Emily even though she knew it was postural hypotension", "valence": -0.5, "keywords": ["frightened", "dizzy", "worried", "fright"]},
        {"type": "fact",  "content": "Emily has postural hypotension — dizziness when standing up too quickly", "valence": None, "keywords": ["postural hypotension", "dizzy", "standing", "blood pressure", "health"]},
    ],
    21: [
        {"type": "event", "content": "Michael drove Emily to the garden centre to buy new plants", "valence": None, "keywords": ["Michael", "garden centre", "plants", "outing"]},
        {"type": "event", "content": "Stopped for coffee and a scone with Michael on the way home", "valence": None, "keywords": ["coffee", "scone", "Michael", "café stop"]},
        {"type": "event", "content": "Planted trailing geraniums in the window boxes when home", "valence": None, "keywords": ["geraniums", "window boxes", "planting", "garden"]},
        {"type": "mood",  "content": "Emily felt cheered up by the outing and the company with Michael", "valence": 0.75, "keywords": ["cheered", "company", "cheerful", "Michael", "outing"]},
        {"type": "fact",  "content": "Michael is a close friend who regularly helps Emily with outings and errands", "valence": None, "keywords": ["Michael", "friend", "help", "outings", "kind"]},
    ],
    22: [
        {"type": "event", "content": "Listened to Ella Fitzgerald and Frank Sinatra records while knitting", "valence": None, "keywords": ["Ella Fitzgerald", "Frank Sinatra", "records", "knitting"]},
        {"type": "event", "content": "Had a small glass of sherry before supper as a little luxury", "valence": None, "keywords": ["sherry", "supper", "luxury", "evening"]},
        {"type": "mood",  "content": "Emily felt deeply settled and peaceful — the afternoon felt like meditation", "valence": 0.85, "keywords": ["settled", "peaceful", "content", "meditative"]},
        {"type": "fact",  "content": "Emily is knitting a navy cardigan for Tommy — working on the complicated yoke pattern", "valence": None, "keywords": ["knitting", "cardigan", "Tommy", "navy", "yoke pattern"]},
    ],
    23: [
        {"type": "event", "content": "Woke at 5am and sat in the garden with tea watching the sunrise", "valence": None, "keywords": ["5am", "garden", "tea", "sunrise", "early morning"]},
        {"type": "event", "content": "A fox came through the hedge and looked straight at Emily in the garden", "valence": None, "keywords": ["fox", "hedge", "garden", "wildlife", "bold"]},
        {"type": "mood",  "content": "Emily felt completely at peace — not lonely at all in the early morning garden", "valence": 0.9, "keywords": ["peaceful", "not lonely", "quiet", "content", "at peace"]},
        {"type": "fact",  "content": "Emily loves early mornings in the garden when it is quiet and the birds are active", "valence": None, "keywords": ["early morning", "garden", "quiet", "birds", "favourite time"]},
    ],
    24: [
        {"type": "event", "content": "Cooking leg of lamb with rosemary and roast potatoes for Sunday lunch", "valence": None, "keywords": ["leg of lamb", "rosemary", "roast potatoes", "Sunday lunch"]},
        {"type": "event", "content": "Sarah, Michael, and Tommy are all coming for Sunday lunch today", "valence": None, "keywords": ["Sarah", "Michael", "Tommy", "Sunday lunch", "family gathering"]},
        {"type": "mood",  "content": "Emily feels completely ready and happy — loves having a full table", "valence": 0.9, "keywords": ["ready", "happy", "full table", "Sunday", "family"]},
        {"type": "fact",  "content": "Sunday lunch with the whole family is one of Emily's favourite things", "valence": None, "keywords": ["Sunday lunch", "family", "favourite", "tradition", "roast"]},
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

    low_mood = {1, 8, 9, 11, 14, 18, 20}   # crying/grief, bad nights, memory worry, hip pain, dizzy
    pos_mood = {0, 2, 6, 7, 10, 17, 19, 22, 23, 24}  # red kite, Tommy news, book club, play, Dorothy lunch, family visit, bright morning, records, sunrise, Sunday roast
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

    pos_w = {'lovely','wonderful','good','happy','great','nice','beautiful','well','bright','proud','warm','relaxed',
             'satisfied','fascinating','peaceful','lucky','content','stimulated','fond','cheerful','settled','full',
             'ready','encouraged','better','pleased','delicious','perfect','extraordinary','luxury'}
    neg_w = {'tired','anxious','sad','miss','low','poorly','shaken','groggy','unease','hurt','worried','slow','waking',
             'dreadful','frightened','frustrated','foggy','painful','wretched','frightening','absence','grief',
             'useless','difficulty','fright','unsettled','cry','racing','swimmy','dark'}
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
             'proud','warm','relaxed','satisfied','fascinating','peaceful','lucky','content',
             'stimulated','fond','cheerful','settled','full','ready','encouraged','better',
             'pleased','delicious','perfect','extraordinary','luxury'}
    neg_w = {'tired','anxious','sad','miss','low','poorly','shaken','groggy','unease',
             'hurt','worried','slow','waking','dreadful','frightened','frustrated','foggy',
             'painful','wretched','absence','grief','useless','fright','unsettled','cry',
             'racing','swimmy','dark'}
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

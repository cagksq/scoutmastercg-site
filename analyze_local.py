#!/usr/bin/env python3
"""
Local analysis script — SRT-based timed transcript with named sections.
Sections are explicit dicts; unnamed groups just get quiet timestamps.
Run from the Hugo site root:
  cd "/Users/clarkegreen 1/mysite"
  python3 analyze_local.py
"""

import os
import re

TRANSCRIPTS_DIR    = "transcripts"
PODCASTS_DIR       = "content/podcasts"
TRANSCRIPT_MD_DIR  = "content/transcripts"
FORCE              = True
GAP_THRESHOLD      = 4.0
PARA_GAP           = 0.8   # seconds — internal pause after sentence end → new paragraph
PARA_MIN_CHARS     = 150   # don't break unless this many chars accumulated
PARA_MAX_CHARS     = 550   # force a break at any sentence-end pause once over this
EMAIL_GAP          = 3.0   # seconds — boundary between individual emails in a MAILBAG section
EMAIL_SECTION_TITLES = {"MAILBAG", "LISTENERS EMAIL"}

# Transcription corrections applied to all generated transcript text
TRANSCRIPT_FIXES = [
    (re.compile(r'\bWeeblow\b',              re.IGNORECASE), 'Webelos'),
    (re.compile(r'\bWeeblos\b',              re.IGNORECASE), 'Webelos'),
    (re.compile(r'\bWeeblo\b',               re.IGNORECASE), 'Webelos'),
    (re.compile(r'\bScout\s+Mastership\b',   re.IGNORECASE), 'Scoutmastership'),
    (re.compile(r'\bScoutmaster\s+Ship\b',   re.IGNORECASE), 'Scoutmastership'),
    (re.compile(r'\bScout\s+Masters\b',      re.IGNORECASE), 'Scoutmasters'),
    (re.compile(r'\bScout\s+Master\b',       re.IGNORECASE), 'Scoutmaster'),
    # Host name spelling
    (re.compile(r'\bClark\s+Green\b'),                        'Clarke Green'),
    # Remove transcribed musical/jingle filler: same word (≤6 chars) repeated 4+ times
    (re.compile(r'\b(\w{1,6})\b(?:[.!?,\s]+\b\1\b){3,}[.!?,\s]*', re.IGNORECASE), ''),
    # EP21 Brick Mason intro — transcription fixes
    (re.compile(r"\bI'?m\s+marked\s+by\s+a\s+lack\s+of\s+truth\b", re.IGNORECASE),
     'In a time marked by a lack of truth'),
    (re.compile(r"\bThe\s+world\s+turns\s+to\s+Mason,\s+Scoutmaster\b", re.IGNORECASE),
     'the world turns to Brick Mason, Scoutmaster'),
    (re.compile(r"\bRichard\s+Mason\s+Scoutmaster\b", re.IGNORECASE),
     'Brick Mason, Scoutmaster'),
    # EP22 "All-Time Favorite Boy Scout" music break lyrics
    (re.compile(r"(?:He'?s|You'?re|Yeah,?\s+you'?re)\s+my\s+favorite\s+all-time\s+Boy\s+Scout\.?\s*", re.IGNORECASE), ''),
    (re.compile(r"(?:You\s+were|Yeah,?\s+you\s+were)\s+always\s+on\s+the\s+beat,\s+boy,\s+beat,\s+boy\.?\s*", re.IGNORECASE), ''),
    (re.compile(r"I'?m\s+hanging\s+in\s+the\s+street,\s+boy,\s+street,\s+boy\.?\s*", re.IGNORECASE), ''),
    (re.compile(r"He\s+was\s+dancing\s+to\s+the\s+beat,\s+boy,\s+beat,\s+boy\.?\s*", re.IGNORECASE), ''),
    # Normalize whitespace left by removals
    (re.compile(r'[ \t]{2,}'), ' '),
]


def is_noise_para(text):
    """Return True if text is transcribed musical filler with no real content.

    Catches paragraphs whose every word is ≤3 chars (pure sounds like Hey, Hi,
    Do, Ba) and paragraphs that are empty or punctuation-only after fixes.
    """
    words = re.findall(r'[a-zA-Z]+', text)
    if not words:
        return True
    return all(len(w) <= 3 for w in words)

def fix_text(t):
    for pattern, repl in TRANSCRIPT_FIXES:
        t = pattern.sub(repl, t)
    return t

EPISODE_URL_BASE = (
    "https://scoutmastercg-podcast.s3.us-east-005.backblazeb2.com/"
    "scoutmaster-podcast-{}.mp3"
)
EPISODE_PAGE_BASE = "/podcasts/episode-{:d}/"

# Recurring/standard section names — excluded from subtitle auto-detection.
# The longest note among non-standard (feature) sections becomes the episode subtitle.
STANDARD_SECTIONS = {"INTRO", "MAILBAG", "LISTENERS EMAIL"}

# sections: list of dicts describing named section breaks.
#   title  — displayed in the Sections index and as a header in the transcript
#   note   — optional subtitle (e.g. joke description, sender names)
#   groups — list of 0-based group indices covered by this section
# Groups not listed in any section appear in the transcript with a plain timestamp only.
ANALYSIS = {
    1: {
        "title":   "Why I became a Scoutmaster — and the ground rules for teaching scouts anything",
        "summary": "Clarke's inaugural episode introduces the podcast and his 25-year Scoutmaster background. He argues that Scouting works because it capitalises on what boys naturally do anyway — form gangs, adopt uniforms, dare each other — and channels those instincts into something constructive rather than outlawing them the way schools do. Includes a cautionary camp story about a Scoutmaster who filled a fire trench with black powder (not smokeless powder) for a dramatic 'fire snake' effect, with predictably explosive results. Opens a multi-episode series on Scout instructional methods: Baden-Powell's principle that effort matters more than expertise, and the foundational rule that adult coaches must stay on the sideline.",
        "tags":    ["scout-instruction", "advancement", "patrol-method", "scoutmasters-job", "scouting-ideals"],
        "sections": [
            {"title": "INTRO", "note": "it occurs to me, for generations, men have looked upon the bald eagle and found great inspiration, yet when the eagle looks upon a bald man, it doesn't seem to affect him at all", "groups": [0, 1]},  # 0:00, 0:50
            {"title": "INSTRUCTIONAL METHODS — INTRODUCTION", "note": "Baden-Powell on effort over expertise; no lectures longer than two minutes, no worksheets, no homework; the coach-player divide — adult leaders stay on the sideline and let the scouts play the game", "groups": [2]},  # 8:40
            {"title": "OUTRO", "note": "", "groups": [3]},  # 18:18
        ],
        "guests":   [],
        "segments": [],
    },
    2: {
        "title":   "Five ways to make the most of your opportunity as a Scout leader",
        "summary": "Five practical principles for every Scout leader: trust the program and its hundred years of refinement; conduct age-appropriate activities; work professionally with other adults even when you disagree; keep perspective and proportion; and focus always on the scouts' success rather than the process. Clarke also shares a story about catching reptiles at camp, and responds to a listener who wrote about Cliff Young — the 61-year-old Australian sheep farmer who won the gruelling 1983 Sydney-to-Melbourne ultramarathon in rubber gumboots, shuffling through five sleepless days — as a parable of unconventional method and the rewards of simply showing up.",
        "tags":    ["scoutmasters-job", "scouts", "training"],
        "sections": [
            {"title": "INTRO", "note": "Somebody once said, there's no such thing as a bad boy. And I agree, I do agree, but some of them can be a real pain every once in a while.", "groups": [0, 1]},  # 0:00, 0:08
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Five ways to make the most of your opportunity as a Scout leader: trust the program; age-appropriate activities; work with other adults; keep perspective; focus on scouts' success", "groups": [1]},  # 0:08 seek_to
            {"title": "STORY FROM CAMP", "note": "Reptiles at camp — a staff member shows up at the Nature Lodge with a pillowcase full of surprises", "groups": [2]},  # 8:18
            {"title": "MAILBAG", "note": "Listener on Cliff Young — 61-year-old Australian farmer who won the 1983 Sydney-to-Melbourne ultramarathon in gumboots using a shuffling stride; a parable of unconventional method and showing up", "groups": [3]},  # 15:47
        ],
        "guests":   [],
        "segments": [],
    },
    3: {
        "title":   "BSA Centenary — one hundred years of the Boy Scouts of America",
        "summary": "Episode three marks the 100th anniversary of the Boy Scouts of America (February 8, 1910). Clarke reads Baden-Powell's founding principles — three simple points about the aim of Scouting, the scout's desire to learn for himself, and working through patrol leaders — and traces W.D. Boyce's discovery of Scouting in London and its rapid spread across America. Also includes early listener mail; a third instalment in the instructional methods series; a story about a troop meeting where boys were milling about aimlessly; and a Scoutmaster's Minute about the value of visiting a troop meeting with open eyes.",
        "tags":    ["scouting-history-ideas", "scout-instruction", "patrol-method", "scoutmasters-job"],
        "sections": [
            {"title": "INTRO", "note": "Whoever first said, 'where there's smoke there's fire' — there is very little chance that person was a Scoutmaster.", "groups": [0, 1]},  # 0:00, 0:08
            {"title": "MAILBAG", "note": "First listener responses — Twitter comments and blog replies to episodes 1 and 2; plus a plug for The Dump, a vast online archive of historical Scouting booklets from Scouts Canada and the British association", "groups": [2]},  # 0:56
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "BSA Centenary — Baden-Powell's three founding principles; W.D. Boyce brings Scouting to America in 1910; one hundred years of the same simple idea spreading around the world", "groups": [3]},  # 3:18
            {"title": "WHAT WOULD YOU DO?", "note": "Scenario about a nationwide Scout movement — structured problem or discussion segment", "groups": [4]},  # 9:50
            {"title": "STORY FROM CAMP", "note": "Boys milling about aimlessly at the start of a troop meeting — a familiar scene", "groups": [5]},  # 17:57
            {"title": "INSTRUCTIONAL METHODS PART 3", "note": "Third instalment of the series on effective Scout instruction methods", "groups": [6]},  # 19:20
            {"title": "SCOUTMASTER'S MINUTE", "note": "Come and visit a troop meeting with me — seeing the troop through a visitor's eyes", "groups": [7, 8]},  # 23:24
        ],
        "guests":   [],
        "segments": [],
    },
    4: {
        "title":   "Merit Badge Days — and what the Scoutmaster's job actually is",
        "summary": "Clarke responds to Mark Bowie of Troop 531 (Orange, CA) on the contentious question of Merit Badge Days. His position: the Scoutmaster's role in advancement is deliberately minimal — he sees only blue cards, not counselors, instruction quality, or scheduling. If a counselor is cutting corners, that's a council advancement committee issue, not a Scoutmaster issue. The episode also covers how to handle scouts who seem to be badge-hunting rather than badge-earning, with a nod to Baden-Powell's warning about badge hunting supplanting badge earning. Ends with a Scoutmaster's Minute on the Scout Law.",
        "tags":    ["advancement", "scoutmasters-job", "merit-badge"],
        "sections": [
            {"title": "INTRO", "note": "An 8-year-old Cub Scout shares his name with someone on the TSA watchlist — 'Weebelos sounds like some kind of call to war. Weebelo, weebelo, weebelo.'", "groups": [0, 1]},  # 0:00, 0:08
            {"title": "LISTENERS EMAIL", "note": "Mark Bowie, Troop 531, Orange CA — asks about Merit Badge Days; Clarke's answer: the Scoutmaster sees only blue cards; counselor quality is a council advancement committee matter, not yours", "groups": [2, 3]},  # 1:25
            {"title": "STORY FROM CAMP", "note": "Brief camp interlude", "groups": [4]},  # 14:23
            {"title": "SCOUTMASTER'S MINUTE", "note": "A scout is trustworthy — the first point of the Scout Law", "groups": [5]},  # 22:01
            {"title": "OUTRO", "note": "", "groups": [6]},  # 24:11
        ],
        "guests":   [],
        "segments": [],
    },
    5: {
        "title":   "Transitioning a Webelos Den Leader into the Scout troop",
        "summary": "When a Webelos den leader crosses into the Scout troop — as Scoutmaster or assistant — the hardest thing is unlearning the instinct to answer questions and fix problems directly. Clarke explains why former den leaders must redirect every scout question to the patrol leader, even when they know the answer, and why watching their former Webelos flounder under a developing patrol leader is not a crisis but the whole point. Also includes a story about a young Scoutmaster's disastrous first hike, a fifth instalment on Scout instructional methods, and a Scoutmaster's Minute about Founders Day — Baden-Powell's birthday, February 22nd.",
        "tags":    ["patrol-method", "scoutmasters-job", "youth-leadership", "scouts"],
        "sections": [
            {"title": "INTRO", "note": "Plato, the Greek philosopher from 400 BC, was apparently a Scoutmaster. He said: 'of all the animals, the boy is the most unmanageable.'", "groups": [0, 1]},  # 0:00, 0:08
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Transitioning Webelos Den Leaders into the Scout troop — redirect every question to the patrol leader; resist the urge to step in; the discomfort of watching your former cubs flounder is the price of building real youth leadership", "groups": [2, 3]},  # 0:55
            {"title": "STORY FROM CAMP", "note": "A young Scoutmaster's first hike — the troop exploded with long-suppressed laughter as he took off the knapsack", "groups": [4, 5]},  # 12:31
            {"title": "SCOUTMASTER'S MINUTE", "note": "Founders Day — February 22nd, Baden-Powell's birthday; a moment to acknowledge the founder of the movement", "groups": [6, 7]},  # 20:57
        ],
        "guests":   [],
        "segments": [],
    },
    6: {
        "title":   "What 'Scoutmaster' actually means — and moving your troop from adult-led to youth-led",
        "summary": "Commissioner Andy's essay on why the word 'Scoutmaster' has caused a century of trouble in America: Baden-Powell borrowed 'schoolmaster' from British education to mean 'teacher of scouts,' but Americans translated 'master' as boss. The UK, Australia, and Canada have all moved to 'Scout leader' or 'Scouter'; the US alone retained a title that implies command rather than service. Clarke also introduces the moccasin telegraph — the informal grapevine that runs through any troop — and begins a multi-part series on moving a troop from adult-led to youth-led. Listener mail and a Scoutmaster's Minute on the Scout Law ('a scout is cheerful').",
        "tags":    ["scoutmasters-job", "youth-leadership", "patrol-method", "scouting-history-ideas"],
        "sections": [
            {"title": "INTRO", "note": "Bill Cosby on being a Boy Scout in Philadelphia — loading up at the Army-Navy store, catching a trolley to hike in Fairmount Park", "groups": [0]},  # 0:00
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Andy's essay on the word 'Scoutmaster' — in America 'master' means boss, not teacher; the UK, Australia, and Canada all use Scout leader instead; the naming decision a hundred years ago still shapes how adults misunderstand their role", "seek_to": 161},  # 2:41
            {"title": "ADULT-TO-YOUTH LEADERSHIP PART 1", "note": "First instalment of a series on moving a troop from adult-led to youth-led — the moccasin telegraph; what changes and what doesn't", "groups": [1, 2]},  # 12:23
            {"title": "MAILBAG", "note": "Listener letters", "groups": [3]},  # 13:50
            {"title": "SCOUTMASTER'S MINUTE", "note": "A scout is cheerful — the ninth point of the Scout Law", "groups": [4, 5]},  # 21:28
        ],
        "guests":   [],
        "segments": [],
    },
    7: {
        "title":   "Scoutmaster or legislator — why manuals and contracts don't build responsible scouts",
        "summary": "Clarke confesses his early mistake: writing a detailed troop policy manual and making patrol leaders sign contracts, in the hope that formalising expectations would produce responsible youth leaders. It didn't. The manual was quoted to miscreants and ignored by everyone else; the contracts were equally useless. The real work is mentoring, coaching, and accepting that attendance and discipline problems are not problems to be solved — they are the cost of doing business with adolescents. Includes a camp story about George (a former staff member whose son is about to join the troop), the second instalment of the adult-to-youth leadership series, and a Scoutmaster's Minute on giving.",
        "tags":    ["scoutmasters-job", "youth-leadership", "scouts", "patrol-method"],
        "sections": [
            {"title": "INTRO", "note": "From Bryce Cochran's 1952 book: 'I rapidly acquired a reputation for supernatural wisdom by saying nothing… he's not saying nothing, but he's thinking plenty, I heard one boy mutter to another.'", "groups": [0, 1]},  # 0:00, 0:08
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Scoutmaster vs legislator — writing a troop manual and making scouts sign contracts produces nothing; discipline and attendance problems are not problems to solve, they are the price of working with adolescents; the answer is coaching and mentoring", "groups": [2, 3]},  # 1:00
            {"title": "STORY FROM CAMP", "note": "George, a former camp staff member whose son is about to join the troop — and the day they struck the colours together", "groups": [4]},  # 11:26
            {"title": "SCOUTMASTER'S MINUTE", "note": "Giving — thinking of the people of Haiti and Chile; if you live in the US, you have it pretty good, and that's a reason to help", "seek_to": 1208},  # 20:08
        ],
        "guests":   [],
        "segments": [],
    },
    8: {
        "title":   "Ten things adult leaders do that frustrate their youth leadership",
        "summary": "Clarke works through ten ways adult leaders undermine their own scouts: talking too much, using coercion to narrow the scouts' options, nitpicking how things are done, and seven more. He's speaking from experience — these are things he has done and sometimes still does. Delivered as the third instalment of the adult-to-youth leadership series. Opens with Green Bar Bill's easy-chair test from the 1939 Scoutmaster's Handbook: if you can sit in the corner without lifting a finger from opening to closing, your troop is genuinely run on the patrol method. Includes a story about the best Fourth of July Clarke ever spent at summer camp.",
        "tags":    ["scoutmasters-job", "youth-leadership", "patrol-method", "scouts"],
        "sections": [
            {"title": "INTRO", "note": "Green Bar Bill's easy-chair test from the 1939 Scoutmaster's Handbook — sink into the chair after the opening ceremony and sit without lifting a finger; if the troop runs fine without you, you're doing it right", "groups": [0, 1]},  # 0:00, 0:08
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Ten things adult leaders do that frustrate youth leadership: talking too much, coercion, nitpicking — and seven more; Clarke speaks from personal experience as someone still on the learning curve", "groups": [2, 3]},  # 1:28
            {"title": "ADULT-TO-YOUTH LEADERSHIP PART 3", "note": "Third and final instalment of the series on moving a troop from adult-led to youth-led", "groups": [4]},  # 16:05
        ],
        "guests":   [],
        "segments": [],
    },
    9: {
        "title":   "Second chances — why Clarke has never kicked a scout out of his troop",
        "summary": "Drawing on recent brain science showing that adolescent decision-making is physically limited — not a choice to be irrational but a developmental reality — Clarke makes the case for second chances in Scouting. In over two decades he has dealt with fights, lies, theft, smoking, and scouts charged with crimes, but has never expelled anyone. He then describes taking in a Star Scout who was asked to leave a troop across town over a single incident: the evidence of four years of work, a dozen merit badges, four boards of review, and held positions of responsibility argues strongly for giving him a second chance. Clarke's prediction: this scout will make Eagle. Includes a story drawn from a favourite author and recommended resources.",
        "tags":    ["scouts", "scoutmasters-job", "advancement", "scouting-ideals"],
        "sections": [
            {"title": "INTRO", "note": "From Bryce Cochran's 1952 book: managing a group of boy hikers has 'somewhat the same problems that faced Moses in managing the Exodus, or Napoleon in supervising the retreat from Moscow.'", "groups": [0, 1]},  # 0:00, 0:10
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Second chances — adolescent brains are physically developing, not choosing to be irrational; Clarke has never expelled a scout in 25 years; the case for taking in a scout who was dismissed elsewhere: four years of work, a dozen merit badges, boards of review, and one incident", "groups": [2]},  # 1:10
            {"title": "WHAT WOULD YOU DO?", "note": "Scenario-based discussion — nine out of ten problems you face as a scout leader are not really problems", "groups": [3, 4, 5, 6]},  # 12:05
            {"title": "SCOUTMASTER'S MINUTE", "note": "A Scout is brave — he might be afraid, but he can still face danger; courage to stand for what he thinks is right", "groups": [7]},  # 21:01
        ],
        "guests":   [],
        "segments": [],
    },
    10: {
        "title":   "The patrol — the irreducible unit of Scouting",
        "summary": "Baden-Powell called the patrol system 'the one essential feature in which Scout training differs from all other organisations' — and where it is properly applied it is 'absolutely bound to bring success.' Clarke explains what this means practically in a modern troop where scouts are driven to meetings rather than living in the same neighbourhood: turning one meeting per month into a pure patrol meeting with no troop trappings, and sending patrols out independently on campouts to plan, cook, and run their own programme. Also includes a story about camp cleanup and a game where scouts bid for privileges using pieces of collected rubbish, and thoughts on choosing the right troop and handling difficult scouts.",
        "tags":    ["patrol-method", "scoutmasters-job", "outdoors", "scouts"],
        "sections": [
            {"title": "INTRO", "note": "Three Scout leaders reach a river — one gets out a hatchet and rope for a pioneering crossing, one swims, the woman asks directions and finds a bridge fifty yards upstream.", "groups": [0, 1]},  # 0:00, 0:08
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "The patrol system as the irreducible unit of Scouting — Baden-Powell's essential feature; how to make patrols function when scouts don't live near each other; one patrol-only meeting per month; camping by patrol without adult oversight", "groups": [2, 3]},  # 0:55
            {"title": "STORY FROM CAMP", "note": "Camp cleanup — the littered campsite at the end of every outing; a game where scouts bid for privileges using pieces of collected rubbish", "groups": [4, 5]},  # 11:32
        ],
        "guests":   [],
        "segments": [],
    },
    101: {
        "title":   "Scoutmaster conferences and the boy-led troop",
        "summary": "Episode 101 features the regular panel of Tom Gillard, Larry Geiger, and Walter Underwood discussing two key Scouting topics. The first segment covers Scoutmaster conferences, emphasizing they are conversations to connect with Scouts—not pass/fail evaluations—and that no Scout can fail one. The panel then addresses a question from Andre Crawford about maintaining the boy-led principle while ensuring effective troop operations, with advice on asking guiding questions rather than directing and trusting youth leadership development. The episode also covers Journey to Excellence, updates to the Eagle Scout project workbook, and the importance of mandatory adult training requirements.",
        "tags":    ["scoutmaster-conference", "boy-led-troop", "youth-leadership", "advancement", "eagle-scout", "journey-to-excellence", "patrol-method"],
        "sections": [
            {
                "title":  "INTRO",
                "note":   "The cook always made the best batter",
                "groups": [0, 1],
            },
            {
                "title":  "MAILBAG",
                "note":   "Will Hensman, Howard Jones, Larry Geiger, Peter LaRue, Steve Borger, Jeff Pearson, and others — 100th episode congratulations",
                "groups": [2],
            },
            {
                "title":  "SCOUTMASTER PANEL DISCUSSION",
                "note":   "Scoutmaster conferences and the boy-led troop",
                "groups": [3, 4],
            },
            {"title": "OUTRO", "note": "", "groups": [5]},
        ],
        "guests":   [],
        "segments": ["Opening Joke", "Mailbag", "Scoutmaster Conference Discussion", "Panel Discussion"],
    },

    102: {
        "title":   "The patrol system as Scouting's one essential feature",
        "summary": "Episode 102 presents an extended Scoutmastership segment tracing the origins of the Scouting movement from Ernest Thompson Seton's Woodcraft Indians to Baden Powell's development of the patrol system. Drawing extensively from Baden Powell's Aids to Scoutmastership, the episode explains why the patrol method is the one essential feature that distinguishes Scouting from all other organizations. Clarke Green argues that giving boys real, freehanded responsibility within small peer groups is the engine of character development and that a troop without an effective patrol system is not truly doing Scouting. The episode also announces an upcoming series of interviews with notable Eagle Scouts celebrating the centenary of the Eagle Scout Award in 2012.",
        "tags":    ["patrol-method", "patrol-system", "scouting-history", "character-development", "boy-led-troop", "scoutmastership", "eagle-scout"],
        "sections": [
            {
                "title":  "INTRO",
                "note":   "You can't tell a brook by its clover",
                "groups": [0, 1],
            },
            {
                "title":  "MAILBAG",
                "note":   "Ray Britton (Troop 42, Oak Ridge TN)",
                "groups": [2],
            },
            {
                "title":  "SCOUTMASTERSHIP IN 7 MINUTES",
                "note":   "The patrol system as Scouting's one essential feature",
                "groups": [4],
            },
            {"title": "OUTRO", "note": "", "groups": [5]},
        ],
        "guests":   [],
        "segments": ["Opening Joke", "Mailbag", "Scoutmastership Segment"],
    },

    105: {
        "title":   "An Eagle Scout parent on raising his own Scout",
        "summary": "Episode 105 features a candid field interview with Dave, an Eagle Scout and adult leader, who shares his experience with Scouting from three perspectives: as a boy whose mother enrolled him after his father's death, as a parent navigating his son's involvement including a temporary dropout, and as an adult leader who found renewed purpose through the program. The conversation explores the difficult balance between encouraging a Scout's participation and respecting his autonomy, showing that honoring a Scout's decision to quit can lead to a more committed voluntary return. The episode also answers a practical advancement question: a first-year Scout serving informally in a leadership role can receive advancement credit, since the requirement does not specify the position must be elected.",
        "tags":    ["parenting", "youth-leadership", "eagle-scout", "advancement", "leadership-positions", "scout-retention", "troop-management"],
        "sections": [
            {
                "title":  "INTRO",
                "note":   "Moss grows on the outside of the tree",
                "groups": [0, 1],
            },
            {
                "title":  "MAILBAG",
                "note":   "Dave Legge (Troop 35, Mount Claire VA), Scott Cormier",
                "groups": [2],
            },
            {
                "title":  "INTERVIEW WITH EAGLE PARENT",
                "note":   "Eagle Scout Dave on raising his son through doubt, dropout, and Eagle — and the parent's dilemma of encouraging without pushing",
                "groups": [3],
            },
            {
                "title":  "LISTENERS EMAIL",
                "note":   "Bill Van Zant (Troop 43, Urbandale IA) asks whether a Scout filling an unelected leadership role can count it toward rank advancement",
                "groups": [5],
            },
            {"title": "OUTRO", "note": "", "groups": [6]},
            # Group 4 (musical interlude) — unnamed
        ],
        "guests":   ["Dave"],
        "segments": ["Opening Joke", "Mailbag", "Guest Interview", "Email Q&A"],
    },

    12: {
        "title":   "Is scouting worth your time?",
        "summary": "Clarke Green asks whether the hundreds of volunteer hours devoted to a Scout troop really matter, and answers with the story of Scoutmaster John Sexton and his Scout Otha Thornton, who went on to become a lieutenant colonel, served on the White House communications staff, and helped rebuild Scouting in Iraq during his deployment.",
        "tags":    ["volunteer-leadership", "eagle-scout", "scouting-impact", "leadership-development"],
        "sections": [
            {"title": "INTRO", "note": "Once you decide to become a volunteer leader, somebody says it's only an hour a week", "groups": [0, 1]},
            {"title": "INTERVIEW", "note": "Lt. Col. Otha Thornton — Eagle Scout, White House communications staff, and rebuilding Scouting in Iraq", "groups": [2]},
            {"title": "OUTRO", "note": "", "groups": [3]},
        ],
        "guests":   [],
        "segments": [],
    },

    21: {
        "title":   "Recruiting Scouts",
        "summary": "Clarke Green discusses the two paths to recruiting new Scouts—transitioning Webelos and reaching everyone else through one-on-one outreach rather than wholesale methods. The episode also returns to the story of Scoutmaster Brick Mason and addresses a listener question about troop leadership dynamics.",
        "tags":    ["recruiting", "webelos", "troop-management", "youth-leadership"],
        "sections": [
            {"title": "INTRO", "note": "Comedian John Panette: a raccoon wants the sandwich", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Recruiting Scouts: Webelos and everyone else", "groups": [2]},
            {"title": "MAILBAG", "note": "Troop 24 — reader response", "groups": [3]},
            {"title": "BRICK MASON", "note": "Mason leads his Scouts up a steep mountain — gloriously", "seek_to": 662},
            {"title": "LISTENERS EMAIL", "note": "Listener question about troop leadership", "groups": [5, 6]},
            {"title": "OUTRO", "note": "", "groups": [7]},
            # Group 4 (interstitial) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    22: {
        "title":   "A special about summer camp",
        "summary": "Clarke Green presents a summer camp special: a former camp director shares tips for Scoutmasters on pacing yourself and staying out of the way, followed by reflections on homesickness at camp — how to recognize it, understand it, and handle it well.",
        "tags":    ["summer-camp", "scoutmaster-role", "patrol-method", "homesickness"],
        "sections": [
            # Groups 0+1 merge (gap at 2:03 = exactly 4.0s, not >threshold); intro + Alan's email both land in group 1
            {"title": "INTRO", "note": "The Scout with seven pairs of socks — efficient, but not right", "groups": [0, 1]},
            {"title": "LISTENERS EMAIL", "note": "Alan on recruiting challenges — why the retail (one-on-one) method beats wholesale outreach", "seek_to": 137},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Summer camp tips for Scoutmasters — pacing yourself, staying out of the way, and letting Scouts lead", "groups": [2]},
            {"title": "MUSIC BREAK", "note": "All-Time Favorite Boy Scout", "seek_to": 924},
            {"title": "SCOUTMASTER'S MINUTE", "note": "The homesick Scout — how to recognize, understand, and handle homesickness at summer camp", "seek_to": 975},
            {"title": "OUTRO", "note": "", "seek_to": 1435},
            # Group 3 (outro) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    23: {
        "title":   "The Scout uniform and high adventure planning, part 1",
        "summary": "Clarke Green discusses the Scout uniform as a program tool rather than a rule to enforce, and continues the high adventure planning series. A hiking song is played for Troop 175 from Niles, Illinois, who were listening to the podcast on the road to an outing.",
        "tags":    ["scout-uniform", "high-adventure", "troop-management", "program-tools"],
        "sections": [
            {"title": "INTRO", "note": "A song for Troop 175, Niles IL — listening in the van", "groups": [0, 1]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "The Scout uniform as a program tool", "groups": [3]},
            {"title": "HIGH ADVENTURE PLANNING", "note": "Part 1 — what is a high adventure trip and how to start building a troop-based program", "seek_to": 689},
            {"title": "OUTRO", "note": "", "seek_to": 1216},
            # Groups 2 (interstitial), 4, 5, 6 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    24: {
        "title":   "Leadership groups, a snake story, and high adventure, part 2",
        "summary": "A long episode covering the three central leadership groups of a Scout troop in Scoutmastership, followed by a listener-requested story about a copperhead snake discovered under the patrol campsite platform, and the second installment of the high adventure planning series.",
        "tags":    ["leadership", "scoutmastership", "high-adventure", "patrol-leader", "summer-camp"],
        "sections": [
            {"title": "INTRO", "note": "Scoutmaster on the psychiatrist's couch: too tense", "groups": [0, 1]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "The three central leadership groups of a Scout troop", "groups": [2]},
            {"title": "STORY FROM CAMP", "note": "A copperhead snake found coiled under the sleeping platform", "groups": [3, 4, 5, 6, 7, 8]},
            {"title": "HIGH ADVENTURE PLANNING", "note": "Part 2 — building out the details: crew formation, gear, permits, and transportation", "seek_to": 1212},
            {"title": "OUTRO", "note": "", "groups": [10]},
        ],
        "guests":   [],
        "segments": [],
    },

    25: {
        "title":   "Patrol logs and high adventure planning, part 3",
        "summary": "A broken paddle 75 yards from the dock after a week-long canoe trip becomes the perfect illustration of why patrol logs and trip reports matter. Clarke covers patrol logs in depth, followed by a Scoutmaster's Minute on persistence, and wraps up the three-part series on building a troop-based high adventure program.",
        "tags":    ["patrol-logs", "high-adventure", "trip-planning", "canoe-tripping"],
        "sections": [
            {"title": "INTRO", "note": "A week of paddling — the paddle breaks 75 yards from the dock", "groups": [0, 1]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Patrol logs — trip records as a tool for improving patrols and building the program", "seek_to": 194},
            {"title": "SCOUTMASTER'S MINUTE", "note": "Gutzon Borglum and Mount Rushmore — chipping away at the rock as a metaphor for persistence in Scoutmaster work", "groups": [2]},
            {"title": "HIGH ADVENTURE PLANNING", "note": "Part 3 — training requirements, safety preparation, and what it takes to run a troop-based high adventure trip", "groups": [3]},
            {"title": "OUTRO", "note": "", "seek_to": 1238},
        ],
        "guests":   [],
        "segments": [],
    },

    26: {
        "title":   "Menu planning and the future of your unit",
        "summary": "Clarke Green answers a question from Scoutmaster Ray Britton about cooking and menu planning for Scout outings, then continues the series on planning the future of your unit—asking what Scouting should look like in your community in the next few years.",
        "tags":    ["menu-planning", "cooking", "troop-planning", "unit-management"],
        "sections": [
            {"title": "INTRO", "note": "Waterproof tents, nonstick pans — challenges not warnings", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Ray Britton (TN) on cooking and menu planning for Scout outings", "groups": [2]},
            {"title": "PLANNING THE FUTURE OF YOUR SCOUT UNIT", "note": "Part 1 — where will your unit be in five years?", "groups": [3]},
            {"title": "OUTRO", "note": "", "groups": [6]},
            # Groups 4, 5 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    27: {
        "title":   "Summer music special",
        "summary": "A special episode recorded while Clarke is away at Scout camp, featuring a curated selection of scouting-related music—jazz renditions of campfire classics, folk songs, and traditional Scout tunes—with commentary on the artists and where to find the recordings.",
        "tags":    ["music", "summer-camp", "scout-songs"],
        "sections": [
            {"title": "INTRO", "note": "Jazz renditions of campfire classics and Scout songs", "groups": [0, 1]},
            {"title": "OUTRO", "note": "", "groups": [8]},
            # Groups 2–7 (music segments) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    28: {
        "title":   "Troop meetings and the Scoutmaster's role",
        "summary": "Clarke Green begins a multi-part series on troop meetings, explaining what the Scoutmaster's role should and shouldn't be—setting things in motion and stepping back to let Scouts work through what looks like organized chaos. Includes a Scoutmaster's Minute on the BSA's 100th anniversary.",
        "tags":    ["troop-meetings", "scoutmaster-role", "youth-leadership", "patrol-method"],
        "sections": [
            {"title": "INTRO", "note": "First time in a canoe: are we going to fall out?", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Liberty Frederick on over-volunteering; troop meetings and the Scoutmaster's role, part 1", "groups": [2]},
            {"title": "PLANNING THE FUTURE OF YOUR SCOUT UNIT", "note": "Part 2 — minimum annual membership to sustain your unit", "groups": [3]},
            {"title": "OUTRO", "note": "", "groups": [4]},
        ],
        "guests":   [],
        "segments": [],
    },

    29: {
        "title":   "Troop meetings and planning ahead, part 2",
        "summary": "Clarke Green continues the troop meetings series, using the story of a painter's chaotic-looking studio as a metaphor for the productive disorder of a well-run Scout meeting—where what looks like a mess is actually Scouts learning. Also continues the series on planning the future of your unit.",
        "tags":    ["troop-meetings", "scoutmaster-role", "youth-leadership", "unit-planning"],
        "sections": [
            {"title": "INTRO", "note": "Two kayakers in the cold: you can't have your kayak and heat it too", "groups": [0, 1]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "The artist's studio — what looks like chaos is Scouts at work", "seek_to": 102},
            {"title": "SCOUTMASTER'S MINUTE", "note": "Baden-Powell on 'Be Prepared' — prepared for what? Any old thing", "seek_to": 463},
            {"title": "PLANNING THE FUTURE OF YOUR SCOUT UNIT", "note": "Part 3 — who are your key unit leaders for the next five years?", "seek_to": 628},
            {"title": "LISTENERS EMAIL", "note": "Timothy Westron — on a Scout who earned Eagle at 13 and kept going", "groups": [3]},
            {"title": "OUTRO", "note": "", "seek_to": 1201},
        ],
        "guests":   [],
        "segments": [],
    },

    30: {
        "title":   "Troop meetings and the future of your unit, part 4",
        "summary": "Recorded while at Algonquin Provincial Park in Ontario, Clarke Green wraps up the troop meetings series with Baden-Powell's century-old advice about trusting patrol leaders and concludes the four-part series on planning the future of your Scout unit. Includes a Scoutmaster's Minute.",
        "tags":    ["troop-meetings", "unit-planning", "baden-powell", "patrol-leader", "high-adventure"],
        "sections": [
            {"title": "INTRO", "note": "How to make a million dollars in scouting: first get two million", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Recorded ahead of the trip — two crews heading to Algonquin Provincial Park for paddling and portaging", "groups": [2]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Baden-Powell on trusting patrol leaders; troop meetings part 3", "groups": [3]},
            {"title": "PLANNING THE FUTURE OF YOUR SCOUT UNIT", "note": "Part 4 — financial stability, budgeting, and fundraising", "groups": [4]},
            {"title": "SCOUTMASTER'S MINUTE", "note": "Ernest Thompson Seton — the fire kindled in the heart", "groups": [5]},
            {"title": "OUTRO", "note": "", "groups": [8]},
            # Groups 6, 7 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    31: {
        "title":   "Self-sufficient Scouts and the boy-led troop",
        "summary": "Back from summer camp and a canoe trip, Clarke Green shares listener letters about troops that have become truly boy-led, including Larry Geiger's story of an Appalachian Trail hike where the Scouts cared for their adult leaders—not the other way around.",
        "tags":    ["boy-led-troop", "youth-leadership", "patrol-method", "summer-camp"],
        "sections": [
            {"title": "INTRO", "note": "Two penguins in a canoe crossing the Sahara Desert", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Larry Geiger and Steve B. on self-sufficient Scouts doing the whole thing themselves", "groups": [2]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Scout decision-making and self-determination in the field — campfire discussion with the crew chief from the Algonquin canoe trip", "seek_to": 350},
            {"title": "OUTRO", "note": "", "seek_to": 1377},
            # Groups 3, 4, 5 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    32: {
        "title":   "A model troop outing and merit badge counselors",
        "summary": "Clarke Green describes the structure of a model Scout troop campout from preparation to execution, emphasizing the independence of youth leadership throughout. The episode also includes a quiz on merit badge counselors to test knowledge of the program's requirements.",
        "tags":    ["troop-outings", "patrol-method", "merit-badges", "youth-leadership"],
        "sections": [
            {"title": "INTRO", "note": "The brain store — a Scoutmaster brain costs $3 million", "groups": [0, 1]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "A model troop outing: adult and Scout roles", "groups": [2]},
            {"title": "QUIZ", "note": "Merit badge counselors — rules, registration, and requirements", "seek_to": 838},
            {"title": "OUTRO", "note": "", "groups": [4]},
            # Group 3 (outro) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    33: {
        "title":   "Den chiefs and a story from summer camp",
        "summary": "Clarke Green discusses den chiefs as a valuable entry-level leadership position for older Scouts, featuring an interview with one of his Scouts about the role and its rewards. The episode also includes the return of the 'This Has Got to Be True' summer camp story segment.",
        "tags":    ["den-chief", "leadership-positions", "summer-camp", "cub-scouts", "patrol-method"],
        "sections": [
            {"title": "INTRO", "note": "Two bear biologists follow the sign: 'Bear Left'", "groups": [0, 1]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Den chiefs: entry-level leadership connecting Boy Scouts to Cub Scout dens", "groups": [2]},
            {"title": "STORY FROM CAMP", "note": "A parent's cell phone call overheard at the campsite", "groups": [4, 5, 6]},
            {"title": "LISTENERS EMAIL", "note": "Scoutmaster Mike (Kentucky) on jumpstarting the patrol method when older Scouts are scarce", "groups": [7]},
            {"title": "OUTRO", "note": "", "seek_to": 1422},
            # Groups 3 (den chief discussion continues), 8 (outro) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    37: {
        "title":   "Preparing for fall and the patrol method in the modern world",
        "summary": "A shorter episode recorded while preparing for a council training event. Clarke reads listener mail, announces upcoming interviews with long-time blog readers and the authors of Working the Patrol Method, and discusses the 20th century realities that shape how patrols can operate independently today.",
        "tags":    ["patrol-method", "adult-training", "troop-management", "youth-leadership"],
        "sections": [
            {"title": "INTRO", "note": "Girl Scout navigation: in case they ever find themselves with a Boy Scout", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Listener mail; preparing for council training; upcoming interviews; 20th century realities of the patrol method", "groups": [2]},
            {"title": "OUTRO", "note": "", "seek_to": 1001},
            # Groups 3, 4 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    38: {
        "title":   "A conversation with Scoutmaster Larry Geiger",
        "summary": "An extended interview with Larry Geiger, Scoutmaster in Cocoa, Florida, who has been a frequent commenter on the blog and podcast. The conversation covers his troop's program, the journey toward a truly boy-led troop, and what success looks like when Scouts can do the whole thing themselves.",
        "tags":    ["interview", "boy-led-troop", "patrol-method", "scoutmaster-stories"],
        "sections": [
            {"title": "INTRO", "note": "Alaska grizzly bears on a ridge", "groups": [0, 1]},
            {"title": "INTERVIEW", "note": "Larry Geiger, Scoutmaster, Cocoa FL — program, boy-led journey, and Scouts who lead themselves", "seek_to": 272},
            {"title": "OUTRO", "note": "", "seek_to": 1817},
            # Group 2 (outro disclaimer) — unnamed
        ],
        "guests":   ["Larry Geiger"],
        "segments": [],
    },

    39: {
        "title":   "Parents meetings, courts of honor, and ceremony",
        "summary": "Clarke Green shares how he runs the annual parents meeting—including a Friends of Scouting presentation and group gear order through Campmor—then covers courts of honor and ceremony in Scouting, arguing for brevity, tradition, and meaning over florid theatrical displays.",
        "tags":    ["parents-meeting", "court-of-honor", "ceremony", "friends-of-scouting", "troop-management"],
        "sections": [
            {"title": "INTRO", "note": "How are Scoutmasters different from Sherlock Holmes? Holmes occasionally had a clue", "groups": [0, 1]},
            {"title": "PARENTS MEETING", "note": "Annual parents meeting — Friends of Scouting presentation and group gear orders through Campmor", "groups": [4]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Courts of honor and ceremony — brevity, tradition, and meaning", "seek_to": 590},
            {"title": "OUTRO", "note": "", "seek_to": 1149},
            # Groups 2, 3 (interstitials) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    40: {
        "title":   "Interview: Working the Patrol Method (40th episode)",
        "summary": "A milestone 40th episode. Clarke reads listener thank-yous celebrating the occasion, then interviews Rob Ferris and Harry Wimbrough, two of the three authors of Working the Patrol Method, on how the patrol method works and why it matters.",
        "tags":    ["patrol-method", "interview", "boy-led-troop", "youth-leadership"],
        "sections": [
            {"title": "INTRO", "note": "Two campaign hats go on a hike — worn out, went on ahead", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "40th episode celebration; listener thank-yous", "groups": [3]},
            {"title": "INTERVIEW", "note": "Rob Ferris and Harry Wimbrough — authors of Working the Patrol Method", "seek_to": 664},
            {"title": "OUTRO", "note": "", "seek_to": 3169},
            # Group 2 (brief transition) — unnamed
        ],
        "guests":   ["Rob Ferris", "Harry Wimbrough"],
        "segments": [],
    },

    41: {
        "title":   "Mike Rowe's letter to an Eagle Scout",
        "summary": "Clarke Green shares a letter Mike Rowe (host of Dirty Jobs) wrote to an Eagle Scout, and a response from Colin who is on the home stretch to Eagle. Includes a Scoutmastership in Seven Minutes on duty to God and the 12th point of the Scout Law, followed by listener emails.",
        "tags":    ["eagle-scout", "leadership-development", "youth-leadership", "scouting-values", "scout-law"],
        "sections": [
            {"title": "INTRO", "note": "The lumberjack who just couldn't cut it — they gave him the axe", "groups": [0, 1]},
            {"title": "LISTENERS EMAIL", "note": "Colin on Eagle Scout perseverance; Jalus transitioning from Cubmaster; listener reactions to the Working the Patrol Method interview", "groups": [3]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Duty to God and a Scout is Reverent — the 12th point of the Scout Law in practice", "seek_to": 420},
            {"title": "MAILBAG", "note": "Listener emails including the Good Turn iPhone app", "groups": [4]},
            {"title": "OUTRO", "note": "", "groups": [5]},
            # Groups 2 (interstitial), 6 (outro tail) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    42: {
        "title":   "Boys will be boys",
        "summary": "Clarke Green opens with Kin Hubbard's line—'Boys will be boys, and so will a lot of middle-aged men'—then covers Contribution Syndrome (great leaders ask questions rather than give answers) and hazing in Scouting.",
        "tags":    ["scoutmastership", "leadership-development", "scout-leaders", "hazing"],
        "sections": [
            {"title": "INTRO", "note": "Kin Hubbard: boys will be boys, and so will a lot of middle-aged men", "groups": [0, 1]},
            {"title": "LISTENERS EMAIL", "note": "Chris (Cubmaster, Sylvania OH) on the podcast", "groups": [3]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Contribution Syndrome — great leaders ask questions rather than give answers", "seek_to": 196},
            {"title": "HAZING", "note": "Recognizing, understanding, and preventing hazing in Scouting", "seek_to": 658},
            {"title": "OUTRO", "note": "", "groups": [4]},
            # Groups 2 (music interstitial), 5, 6 (outro tail) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    43: {
        "title":   "When youth leadership works",
        "summary": "Clarke Green shares a blog post by new Scoutmaster Brian Spellman of Fishers, Indiana, who describes the moment he truly saw his Scouts lead themselves. The episode explores what it looks and feels like when the patrol method actually works—and a listener email touches on similar themes.",
        "tags":    ["patrol-method", "youth-leadership", "boy-led-troop", "scoutmaster-stories"],
        "sections": [
            {"title": "INTRO", "note": "Things Scout leaders say that scouts hear differently: 'lights out, all quiet'", "groups": [0, 1]},
            {"title": "LISTENERS EMAIL", "note": "Brian Spellman on the moment he saw youth leadership actually work; Larry Geiger on why Scouting's real challenges make hazing unnecessary", "groups": [2]},
            {"title": "MAILBAG", "note": "Listener letters on the patrol method and youth leadership", "groups": [3]},
            {"title": "OUTRO", "note": "", "groups": [6]},
            # Groups 4, 5 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    44: {
        "title":   "Adventure, planning, and patrol leader elections",
        "summary": "Clarke Green reflects on Roald Amundsen's famous observation that adventure is just bad planning brought to light by trial, then responds to listener feedback on patrol leader elections from the previous episode.",
        "tags":    ["patrol-leader", "leadership-elections", "advancement", "adventure"],
        "sections": [
            {"title": "INTRO", "note": "Roald Amundsen: an adventure is merely a bit of bad planning", "groups": [0, 1]},
            {"title": "LISTENERS EMAIL", "note": "Larry Geiger and Alan on patrol leader elections — parliamentary vs. constitutional models of troop governance", "groups": [2]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "The honest challenge — why boys stay in Scouting for something better than entertainment", "seek_to": 382},
            {"title": "MAILBAG", "note": "Webelos den leader on encouraging a boy with family difficulties to bridge into Scouts; David on low troop participation rates", "seek_to": 673},
            {"title": "OUTRO", "note": "", "groups": [5]},
        ],
        "guests":   [],
        "segments": [],
    },

    45: {
        "title":   "Boards of review",
        "summary": "Clarke Green discusses how boards of review should be conducted and provides resources for training board members—emphasizing they are not retests of scout skills but meaningful conversations. The episode also marks the blog's fifth anniversary and discusses how to support the podcast and blog.",
        "tags":    ["boards-of-review", "advancement", "troop-management", "eagle-scout"],
        "sections": [
            {"title": "INTRO", "note": "Lost economists: according to the map, we're standing on top of that mountain", "groups": [0, 1]},
            {"title": "LISTENERS EMAIL", "note": "Alan on fun as honest challenge — the night hike as a real adventure for Scouts", "seek_to": 99},
            {"title": "MAILBAG", "note": "Blog's 5th anniversary and podcast support; boards of review — how to run them and train board members", "seek_to": 208},
            {"title": "OUTRO", "note": "", "seek_to": 1042},
            # Groups 3, 4 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    46: {
        "title":   "The scouting process",
        "summary": "Clarke Green explains why Scouting is fundamentally a process—not a production line—and why liberating yourself from the need for measurable outputs is essential to understanding the mission. A Scoutmaster's Minute uses the metaphor of a Scout shirt to describe the Scouting program to non-Scout audiences.",
        "tags":    ["scoutmastership", "scouting-values", "youth-leadership", "scout-oath", "patrol-method"],
        "sections": [
            {"title": "INTRO", "note": "If you think it goes without saying, it almost certainly does not", "groups": [0, 1]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Scouting as a process, not a product — the mission is preparation, not production", "groups": [2]},
            {"title": "SCOUTMASTER'S MINUTE", "note": "The Scout shirt as a metaphor for the Scouting program", "groups": [3]},
            {"title": "OUTRO", "note": "", "seek_to": 892},
            # Groups 4, 5 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    47: {
        "title":   "When scouting works and listener email",
        "summary": "Clarke Green shares listener letters from Larry Geiger, Phil, and Jim, then digs into what Scoutmastership actually means in Scoutmastership in Seven Minutes, and answers Phil's email about leading a young troop with an inexperienced SPL.",
        "tags":    ["scoutmastership", "youth-leadership", "scouting-values", "patrol-method"],
        "sections": [
            {"title": "INTRO", "note": "Evidence Santa Claus might be a Scoutmaster", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Larry Geiger on Scouting as process; Phil and Jim respond to recent episodes", "seek_to": 56},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "What is Scoutmastership anyway?", "seek_to": 211},
            {"title": "LISTENERS EMAIL", "note": "Phil on leading a young troop with an inexperienced SPL", "seek_to": 604},
            {"title": "OUTRO", "note": "", "seek_to": 1240},
        ],
        "guests":   [],
        "segments": [],
    },

    48: {
        "title":   "Listener questions and mailbag",
        "summary": "Clarke Green reads letters from listeners including Ray from Oak Ridge, Tennessee, then digs into two listener questions about troop management and Scouting practice.",
        "tags":    ["troop-management", "listener-questions", "scouting-advice"],
        "sections": [
            {"title": "INTRO", "note": "Scoutmaster goes to his final reward and meets the devil", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Ray (Oak Ridge TN) and listener letters on the podcast", "groups": [2]},
            {"title": "LISTENERS EMAIL", "note": "Goal-setting exercise — aligning youth and adult leadership goals by interviewing each leader individually", "groups": [3]},
            {"title": "WHAT WOULD YOU DO?", "note": "Scouting with Asperger's Syndrome — responses from Christine, Jerry, Walter, and Scouter Adams", "seek_to": 770},
            {"title": "OUTRO", "note": "", "groups": [5]},
            # Group 4 (outro) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    49: {
        "title":   "Mailbag and the patrol method filmstrip",
        "summary": "Clarke Green reads listener mail including a review from Skater Brian on iTunes, then shares the audio from a vintage patrol method filmstrip—a relic from the BSA's past that still has plenty to say about the core of Scout leadership.",
        "tags":    ["patrol-method", "listener-questions", "mailbag", "scouting-history"],
        "sections": [
            {"title": "INTRO", "note": "You know why they didn't make two Yogi Bears? They tried, but somebody made a boo-boo", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Skater Brian (iTunes) and Troop 237 listener letters", "groups": [2]},
            {"title": "PATROL METHOD FILMSTRIP", "note": "Vintage BSA patrol method filmstrip audio — and listener responses", "groups": [3]},
            {"title": "OUTRO", "note": "", "seek_to": 1076},
        ],
        "guests":   [],
        "segments": [],
    },

    50: {
        "title":   "50th episode with Kevin Callan",
        "summary": "A special milestone 50th episode. Listener thank-yous from Davey Gravy and Larry Geiger, plus the launch of a monthly Scoutmaster newsletter. Then a wide-ranging interview with Kevin Callan — Canadian author, canoe enthusiast, and the Happy Camper — on paddling Ontario wilderness, portaging, and the value of wild places.",
        "tags":    ["milestone", "newsletter", "listener-community", "interview", "high-adventure", "canoe"],
        "sections": [
            {"title": "INTRO", "note": "Three pieces of string want milkshakes — one ties himself in a knot and frays his hair", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Davey Gravy and Larry Geiger on podcast 49; announcement of the monthly Scoutmaster newsletter", "groups": [2, 3]},
            {"title": "INTERVIEW", "note": "Kevin Callan — Canadian author and the Happy Camper — on paddling Ontario wilderness, Algonquin Provincial Park, and why a long portage keeps wilderness wild", "seek_to": 328},
            {"title": "OUTRO", "note": "", "groups": [4]},
        ],
        "guests":   ["Kevin Callan"],
        "segments": [],
    },
}


# ---------------------------------------------------------------------------

def parse_srt(srt_path):
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()
    entries = []
    for block in re.split(r'\n\s*\n', content.strip()):
        lines = [l for l in block.strip().splitlines() if l.strip()]
        for i, line in enumerate(lines):
            m = re.match(
                r'(\d+):(\d+):(\d+)[,\.](\d+)\s*-->\s*(\d+):(\d+):(\d+)',
                line.strip()
            )
            if m:
                start = int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3))
                end   = int(m.group(5))*3600 + int(m.group(6))*60 + int(m.group(7))
                entries.append((start, end, " ".join(lines[i+1:])))
                break
    return entries


def group_entries(entries, gap=GAP_THRESHOLD):
    """Return list of (start_s, combined_text, raw_entries) tuples."""
    groups = []
    if not entries:
        return groups
    cs, ct, cr, pe = entries[0][0], [entries[0][2]], [entries[0]], entries[0][1]
    for s, e, t in entries[1:]:
        if s - pe > gap:
            groups.append((cs, " ".join(ct), cr))
            cs, ct, cr = s, [t], [(s, e, t)]
        else:
            ct.append(t)
            cr.append((s, e, t))
        pe = e
    if ct:
        groups.append((cs, " ".join(ct), cr))
    return groups


def split_into_paragraphs(raw_entries, para_gap=PARA_GAP,
                          min_chars=PARA_MIN_CHARS, max_chars=PARA_MAX_CHARS):
    """Split a group's raw SRT entries into paragraphs.

    Breaks at pauses >= para_gap seconds that follow a complete sentence,
    provided at least min_chars have accumulated (prevents single-sentence
    fragments).  Once max_chars are accumulated any sentence-end pause
    >= 0.4s triggers a break, preventing walls of text.
    Returns list of (start_s, text) tuples.
    """
    if not raw_entries:
        return []
    paras = []
    para_start = raw_entries[0][0]
    para_texts = [raw_entries[0][2]]
    prev_end   = raw_entries[0][1]
    for s, e, t in raw_entries[1:]:
        gap = s - prev_end
        accumulated = " ".join(para_texts)
        acc_len = len(accumulated)
        at_sentence_end = bool(re.search(r'[.?!]["\']?\s*$', accumulated.rstrip()))
        should_break = at_sentence_end and (
            (gap >= para_gap and acc_len >= min_chars) or
            (gap >= 0.4     and acc_len >= max_chars)
        )
        if should_break:
            paras.append((para_start, accumulated))
            para_start = s
            para_texts = [t]
        else:
            para_texts.append(t)
        prev_end = e
    if para_texts:
        paras.append((para_start, " ".join(para_texts)))
    return paras


def split_into_emails(raw_entries, email_gap=EMAIL_GAP):
    """For MAILBAG / LISTENERS EMAIL groups: split raw entries into individual
    emails, each returned as a list of (start_s, text) paragraph tuples.

    An email boundary is a gap >= email_gap seconds that follows a sentence end.
    """
    if not raw_entries:
        return []
    emails   = []
    current  = [raw_entries[0]]
    prev_end = raw_entries[0][1]
    for s, e, t in raw_entries[1:]:
        gap = s - prev_end
        accumulated = " ".join(r[2] for r in current)
        if gap >= email_gap and re.search(r'[.?!]["\']?\s*$', accumulated.rstrip()):
            emails.append(split_into_paragraphs(current))
            current = [(s, e, t)]
        else:
            current.append((s, e, t))
        prev_end = e
    if current:
        emails.append(split_into_paragraphs(current))
    return emails



def fmt_time(s):
    s = int(s)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def html_esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


TS_STYLE = 'font-family:monospace;font-size:0.85em;font-weight:bold;margin-right:7px;'


def ts_link(secs, label):
    ts = fmt_time(secs)
    return (
        f'<a href="javascript:void(0)" onclick="seekTo({int(secs)})" '
        f'style="{TS_STYLE}" title="Jump to {ts}">[{label}]</a>'
    )


def build_content(groups, sections):
    # Map group index → section dict (None if unnamed)
    group_section   = {}   # group_idx → section dict
    section_first_g = {}   # section dict id → first group index

    for sec in sections:
        if not sec.get("groups"):
            continue  # seek_to-only section — no group mapping
        first = sec["groups"][0]
        section_first_g[id(sec)] = first
        for g in sec["groups"]:
            group_section[g] = sec

    # --- Section acts list (TAL-style rows, named sections only)
    SVG_PLAY = (
        '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>'
    )
    act_rows = []
    for sec in sections:
        if sec.get("groups"):
            start_s = groups[sec["groups"][0]][0]
        elif "seek_to" in sec:
            start_s = sec["seek_to"]
        else:
            continue
        ts      = fmt_time(start_s)
        secs_i  = int(start_s)
        note    = sec.get("note", "")
        note_html = (
            f'<div class="smcg-act-note">{html_esc(note)}</div>'
        ) if note else ""
        act_rows.append(
            f'<div class="smcg-act">'
            f'<button class="smcg-act-play" onclick="seekTo({secs_i})" title="Jump to {ts}">{SVG_PLAY}</button>'
            f'<div class="smcg-act-body">'
            f'<div class="smcg-act-label">{html_esc(sec["title"])}</div>'
            f'{note_html}'
            f'</div>'
            f'</div>'
        )

    section_index = (
        '<div class="smcg-acts">\n'
        + "\n".join(act_rows)
        + "\n</div>"
    )

    # --- Full transcript (all groups, named ones get bold headers)
    HEADER_STYLE = (
        'margin:1.4em 0 0.2em;padding-bottom:3px;'
        'border-bottom:1px solid #ddd;'
    )
    BODY_STYLE   = 'margin:0.2em 0 0.8em;font-size:0.85rem;line-height:1.8;'
    PLAIN_TS_STYLE = 'margin:1em 0 0.1em;'

    transcript_lines = []
    for i, (start_s, text, _raw) in enumerate(groups):
        sec = group_section.get(i)

        if sec is not None and i == section_first_g[id(sec)]:
            # First group of a named section → bold header
            link  = ts_link(start_s, fmt_time(start_s))
            title = f'<strong>{sec["title"]}</strong>'
            note  = sec.get("note")
            note_html = (
                f' <span style="font-weight:normal;font-style:italic;font-size:0.9em;color:#666;">'
                f'— {html_esc(note)}</span>'
            ) if note else ""
            transcript_lines.append(
                f'<p style="{HEADER_STYLE}">{link}{title}{note_html}</p>'
            )
        elif sec is None:
            # Unnamed group → small plain timestamp
            link = ts_link(start_s, fmt_time(start_s))
            transcript_lines.append(f'<p style="{PLAIN_TS_STYLE}">{link}</p>')
        # else: continuation group of a named section — no new header, just body text

        transcript_lines.append(
            f'<p style="{BODY_STYLE}">{html_esc(text)}</p>'
        )

    transcript_html = "\n".join(transcript_lines)

    return section_index, transcript_html


# ---------------------------------------------------------------------------

def find_md_file(ep_num):
    for fname in sorted(os.listdir(PODCASTS_DIR)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(PODCASTS_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        m = re.search(r'^episode:\s*(\d+)', content, re.MULTILINE)
        if m and int(m.group(1)) == ep_num:
            return fpath, content
    return None, None


def update_frontmatter(fm_body, tags, summary, title):
    # Always replace subtitle (add after episode: line if missing, update if present)
    fm_body = re.sub(r'^subtitle:.*\n',   '', fm_body, flags=re.MULTILINE)
    fm_body = re.sub(r'^transcript:.*\n', '', fm_body, flags=re.MULTILINE)
    if title:
        safe = title.replace('"', "'")
        fm_body = re.sub(
            r'^(episode:\s*\d+\s*\n)',
            rf'\1subtitle: "{safe}"\ntranscript: true\n',
            fm_body, flags=re.MULTILINE
        )
    fm_body = re.sub(r'^tags:\n(  -[^\n]*\n)*', '', fm_body, flags=re.MULTILINE)
    fm_body = re.sub(r'^tags:.*\n',              '', fm_body, flags=re.MULTILINE)
    fm_body = re.sub(r'^summary:.*\n',           '', fm_body, flags=re.MULTILINE)
    fm_body = re.sub(r'^description:.*\n',       '', fm_body, flags=re.MULTILINE)
    tag_lines    = "tags:\n" + "\n".join(f'  - "{t}"' for t in tags) + "\n"
    safe_summary = summary.replace('"', "'").replace('\n', ' ')[:400]
    return fm_body + tag_lines + f'summary: "{safe_summary}"\ndescription: "{safe_summary}"\n'


def build_body_addition(section_index, ep_num):
    ep_page = EPISODE_PAGE_BASE.format(ep_num)
    transcript_link = (
        f'<p style="margin:0.75rem 0 0;">'
        f'<a href="{ep_page}transcript/" class="smcg-transcript-link">Transcript</a>'
        f'</p>'
    )
    return (
        "\n"
        + section_index + "\n\n"
        + transcript_link + "\n"
    )


def build_transcript_md(groups, sections, ep_num, ep_title, subtitle):
    """Generate the content/transcripts/episode-NNN.md file."""
    ep_page = EPISODE_PAGE_BASE.format(ep_num)

    group_section   = {}
    section_first_g = {}
    for sec in sections:
        if not sec.get("groups"):
            continue  # seek_to-only section — injected mid-group if timestamp falls within
        section_first_g[id(sec)] = sec["groups"][0]
        for g in sec["groups"]:
            group_section[g] = sec

    # seek_to-only sections sorted by timestamp — injected between paragraphs
    seekt_sections = sorted(
        [s for s in sections if not s.get("groups") and "seek_to" in s],
        key=lambda s: s["seek_to"],
    )

    def render_tp_hdr(s, t):
        listen_url = f"{ep_page}?t={int(t)}"
        note = s.get("note", "")
        note_html = f'<span class="smcg-tp-note">{html_esc(note)}</span>' if note else ""
        return (
            f'<div class="smcg-tp-hdr">'
            f'<span class="smcg-tp-label">{html_esc(s["title"])}</span>'
            f'{note_html}'
            f'<a href="{listen_url}" class="smcg-tp-listen">&#9654; Listen</a>'
            f'</div>'
        )

    lines    = []
    in_outro = [False]  # set True once OUTRO reached — suppresses remaining transcript content
    for i, (start_s, _text, raw_entries) in enumerate(groups):
        sec = group_section.get(i)

        if sec is not None and i == section_first_g[id(sec)]:
            lines.append('<hr class="smcg-tp-rule">')
            lines.append(render_tp_hdr(sec, start_s))

        # seek_to sections whose timestamp falls within this group
        group_end = groups[i + 1][0] if i + 1 < len(groups) else float("inf")
        pending   = [s for s in seekt_sections if start_s < s["seek_to"] < group_end]
        injected  = set()

        def maybe_inject(para_start):
            for s in pending:
                if s["seek_to"] <= para_start and id(s) not in injected:
                    injected.add(id(s))
                    lines.append('<hr class="smcg-tp-rule">')
                    lines.append(render_tp_hdr(s, s["seek_to"]))
                    if s["title"] == "OUTRO":
                        in_outro[0] = True

        sec_title = sec["title"] if sec else None

        # OUTRO groups: render header only — sign-off boilerplate excluded from transcript
        if sec_title == "OUTRO":
            for s in pending:
                if id(s) not in injected:
                    injected.add(id(s))
                    lines.append('<hr class="smcg-tp-rule">')
                    lines.append(render_tp_hdr(s, s["seek_to"]))
            continue

        if sec_title in EMAIL_SECTION_TITLES:
            emails = split_into_emails(raw_entries)
            for ei, email_paras in enumerate(emails):
                if ei > 0:
                    lines.append('<hr class="smcg-tp-email-sep">')
                for pi, (para_start, para_text) in enumerate(email_paras):
                    maybe_inject(para_start)
                    if in_outro[0]:
                        break
                    para_text = fix_text(para_text).strip()
                    if not para_text or is_noise_para(para_text):
                        continue
                    if pi == 0:
                        lines.append(f'<p class="smcg-tp-from">{html_esc(para_text)}</p>')
                    else:
                        lines.append(f'<p>{html_esc(para_text)}</p>')
        else:
            for para_start, para_text in split_into_paragraphs(raw_entries):
                maybe_inject(para_start)
                if in_outro[0]:
                    break
                para_text = fix_text(para_text).strip()
                if not para_text or is_noise_para(para_text):
                    continue
                lines.append(f'<p>{html_esc(para_text)}</p>')

        # inject any remaining pending headers that never fired (e.g. all paras filtered)
        for s in pending:
            if id(s) not in injected:
                injected.add(id(s))
                lines.append('<hr class="smcg-tp-rule">')
                lines.append(render_tp_hdr(s, s["seek_to"]))
                if s["title"] == "OUTRO":
                    in_outro[0] = True

    safe_title    = ep_title.replace('"', "'")
    safe_subtitle = subtitle.replace('"', "'")
    transcript_url = f"{ep_page}transcript/"

    safe_desc = safe_subtitle or safe_title
    frontmatter = (
        "---\n"
        f'title: "Transcript — {safe_title}"\n'
        f'episode_title: "{safe_title}"\n'
        f'subtitle: "{safe_subtitle}"\n'
        f'description: "Transcript of {safe_title} — {safe_desc}"\n'
        f'summary: "Transcript of {safe_title} — {safe_desc}"\n'
        f'episode_url: "{ep_page}"\n'
        f'url: "{transcript_url}"\n'
        "draft: false\n"
        "---\n"
    )
    return frontmatter + "\n" + "\n".join(lines) + "\n"


def process_episode(ep_num):
    print(f"\n[EP{ep_num:03d}] Processing...")

    srt_path = os.path.join(TRANSCRIPTS_DIR, f"scoutmaster-podcast-{ep_num}.srt")
    if not os.path.exists(srt_path):
        print(f"  SRT not found: {srt_path}")
        return False

    entries = parse_srt(srt_path)
    groups  = group_entries(entries)
    print(f"  Groups: {len(groups)}  {[fmt_time(g[0]) for g in groups]}")

    data        = ANALYSIS[ep_num]
    sections    = data["sections"]
    episode_url = EPISODE_URL_BASE.format(ep_num)

    # Validate section group indices
    for sec in sections:
        for g in sec.get("groups", []):
            if g >= len(groups):
                print(f"  ERROR: section '{sec['title']}' references group {g} but only {len(groups)} groups exist")
                return False

    section_index, transcript_html = build_content(groups, sections)

    # Auto-derive subtitle: longest note among non-standard (feature) sections
    feature_secs = [s for s in sections if s["title"] not in STANDARD_SECTIONS and s.get("note")]
    subtitle = max(feature_secs, key=lambda s: len(s["note"]))["note"] if feature_secs else data.get("title", "")
    print(f"  Subtitle: {subtitle}")

    # Write transcript page
    os.makedirs(TRANSCRIPT_MD_DIR, exist_ok=True)
    transcript_md_path = os.path.join(TRANSCRIPT_MD_DIR, f"episode-{ep_num}.md")
    ep_title = f"Scoutmaster Podcast {ep_num}"
    with open(transcript_md_path, "w", encoding="utf-8") as f:
        f.write(build_transcript_md(groups, sections, ep_num, ep_title, subtitle))
    print(f"  Transcript: {transcript_md_path}")

    md_path, content = find_md_file(ep_num)
    if not md_path:
        print(f"  No Hugo markdown found for episode {ep_num}")
        return False

    fm_match = re.match(r'^(---\n)(.*?)(---\n)(.*)', content, re.DOTALL)
    if not fm_match:
        print(f"  Could not parse frontmatter: {md_path}")
        return False

    fm_open, fm_body, fm_close, body = fm_match.groups()

    # Strip everything after the audio shortcode (all previously generated content)
    body = re.sub(r'({{<\s*audio\b[^>]*>}}).*', r'\1\n', body, flags=re.DOTALL)

    fm_body  = update_frontmatter(fm_body, data["tags"], data["summary"], subtitle)
    new_body = body.rstrip() + "\n" + build_body_addition(section_index, ep_num)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(fm_open + fm_body + fm_close + new_body)

    print(f"  Saved: {md_path}")
    return True


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    episodes = sorted(ANALYSIS.keys())
    print(f"Processing episodes: {episodes}")

    processed = skipped = errors = 0
    for ep in episodes:
        result = process_episode(ep)
        if result is True:    processed += 1
        elif result is False: errors    += 1
        else:                 skipped   += 1

    print(f"\nDone.  Processed: {processed}  Skipped: {skipped}  Errors: {errors}")

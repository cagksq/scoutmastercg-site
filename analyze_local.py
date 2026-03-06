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
            # Group 5 (outro) — unnamed, timestamp only
        ],
        "guests":   [],
        "segments": ["Opening Joke", "Mailbag", "Scoutmaster Conference Discussion", "Panel Discussion"],
    },

    102: {
        "title":   "The patrol system as Scouting's one essential feature",
        "summary": "Episode 102 presents an extended Scoutmastership segment tracing the origins of the Scouting movement from Ernest Thompson Seton's Woodcraft Indians to Baden Powell's development of the patrol system. Drawing extensively from Baden Powell's Aids to Scoutmastership, the episode explains why the patrol method is the one essential feature that distinguishes Scouting from all other organizations. Clark Green argues that giving boys real, freehanded responsibility within small peer groups is the engine of character development and that a troop without an effective patrol system is not truly doing Scouting. The episode also announces an upcoming series of interviews with notable Eagle Scouts celebrating the centenary of the Eagle Scout Award in 2012.",
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
                "groups": [3],
            },
            # Groups 4, 5, 6 (outro) — unnamed, timestamps only in transcript
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
            # Groups 4 (musical interlude), 6 (outro) — unnamed
        ],
        "guests":   ["Dave"],
        "segments": ["Opening Joke", "Mailbag", "Guest Interview", "Email Q&A"],
    },

    12: {
        "title":   "Is scouting worth your time?",
        "summary": "Clark Green asks whether the hundreds of volunteer hours devoted to a Scout troop really matter, and answers with the story of Scoutmaster John Sexton and his Scout Otha Thornton, who went on to become a lieutenant colonel, served on the White House communications staff, and helped rebuild Scouting in Iraq during his deployment.",
        "tags":    ["volunteer-leadership", "eagle-scout", "scouting-impact", "leadership-development"],
        "sections": [
            {"title": "INTRO", "note": "Once you decide to become a volunteer leader, somebody says it's only an hour a week", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Scoutmaster John Sexton and Lt. Col. Otha Thornton — is the time worth it?", "groups": [2]},
            # Group 3 (outro) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    21: {
        "title":   "Recruiting Scouts",
        "summary": "Clark Green discusses the two paths to recruiting new Scouts—transitioning Weeblos and reaching everyone else through one-on-one outreach rather than wholesale methods. The episode also returns to the story of Scoutmaster Brick Mason and addresses a listener question about troop leadership dynamics.",
        "tags":    ["recruiting", "weeblos", "troop-management", "youth-leadership"],
        "sections": [
            {"title": "INTRO", "note": "Comedian John Panette: a raccoon wants the sandwich", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Recruiting Scouts: Weeblos and everyone else", "groups": [2]},
            {"title": "MAILBAG", "note": "Troop 24 — reader response", "groups": [3]},
            {"title": "LISTENERS EMAIL", "note": "Listener question about troop leadership", "groups": [5, 6]},
            # Groups 4 (interstitial), 7 (outro) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    22: {
        "title":   "Patrol logs and high adventure planning, part 1",
        "summary": "Clark Green discusses patrol logs as a practical tool for patrol leaders and senior patrol leaders, and begins a three-part series on creating a troop-based high adventure program—arguing that no troop should go without some form of high adventure activity each year.",
        "tags":    ["patrol-method", "patrol-logs", "high-adventure", "trip-planning", "patrol-leader"],
        "sections": [
            {"title": "INTRO", "note": "The Scout with seven pairs of socks — efficient, but not right", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Patrol logs and high adventure planning part 1", "groups": [2]},
            # Group 3 (outro) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    23: {
        "title":   "The Scout uniform and high adventure planning, part 2",
        "summary": "Clark Green discusses the Scout uniform as a program tool rather than a rule to enforce, and continues the high adventure planning series. A hiking song is played for Troop 175 from Niles, Illinois, who were listening to the podcast on the road to an outing.",
        "tags":    ["scout-uniform", "high-adventure", "troop-management", "program-tools"],
        "sections": [
            {"title": "INTRO", "note": "A song for Troop 175, Niles IL — listening in the van", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "The Scout uniform as a program tool; high adventure planning part 2", "groups": [3]},
            # Groups 2 (interstitial), 4, 5, 6 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    24: {
        "title":   "Leadership groups, a snake story, and high adventure, part 3",
        "summary": "A long episode covering the three central leadership groups of a Scout troop in Scoutmastership, followed by a listener-requested story about a copperhead snake discovered under the patrol campsite platform, and continuing the high adventure planning series.",
        "tags":    ["leadership", "scoutmastership", "high-adventure", "patrol-leader", "summer-camp"],
        "sections": [
            {"title": "INTRO", "note": "Scoutmaster on the psychiatrist's couch: too tense", "groups": [0, 1]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "The three central leadership groups of a Scout troop", "groups": [2]},
            {"title": "STORY FROM CAMP", "note": "A copperhead snake found coiled under the sleeping platform", "groups": [3, 4, 5, 6, 7, 8, 9]},
            # Group 10 (outro) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    25: {
        "title":   "Patrol logs and high adventure planning, part 3",
        "summary": "A broken paddle 75 yards from the dock after a week-long canoe trip becomes the perfect illustration of why patrol logs and trip reports matter. Clark then covers patrol logs in depth and wraps up the three-part series on building a troop-based high adventure program.",
        "tags":    ["patrol-logs", "high-adventure", "trip-planning", "canoe-tripping"],
        "sections": [
            {"title": "INTRO", "note": "A week of paddling — the paddle breaks 75 yards from the dock", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Patrol logs, Scoutmaster's Minute, and high adventure planning part 3", "groups": [2]},
            # Group 3 (outro) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    26: {
        "title":   "Menu planning and the future of your unit",
        "summary": "Clark Green answers a question from Scoutmaster Ray Britton about cooking and menu planning for Scout outings, then continues the series on planning the future of your unit—asking what Scouting should look like in your community in the next few years.",
        "tags":    ["menu-planning", "cooking", "troop-planning", "unit-management"],
        "sections": [
            {"title": "INTRO", "note": "Waterproof tents, nonstick pans — challenges not warnings", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Ray Britton (TN) on cooking and menu planning for Scout outings", "groups": [2]},
            {"title": "MAILBAG", "note": "Planning the future of your Scout unit, part 2", "groups": [3]},
            # Groups 4, 5, 6 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    27: {
        "title":   "Summer music special",
        "summary": "A special episode recorded while Clark is away at Scout camp, featuring a curated selection of scouting-related music—jazz renditions of campfire classics, folk songs, and traditional Scout tunes—with commentary on the artists and where to find the recordings.",
        "tags":    ["music", "summer-camp", "scout-songs"],
        "sections": [
            {"title": "INTRO", "note": "Jazz renditions of campfire classics and Scout songs", "groups": [0, 1]},
            # Groups 2–8 (music segments and outro) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    28: {
        "title":   "Troop meetings and the Scoutmaster's role",
        "summary": "Clark Green begins a multi-part series on troop meetings, explaining what the Scoutmaster's role should and shouldn't be—setting things in motion and stepping back to let Scouts work through what looks like organized chaos. Includes a Scoutmaster's Minute on the BSA's 100th anniversary.",
        "tags":    ["troop-meetings", "scoutmaster-role", "youth-leadership", "patrol-method"],
        "sections": [
            {"title": "INTRO", "note": "First time in a canoe: are we going to fall out?", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Liberty Frederick on over-volunteering and the value of the podcast", "groups": [2]},
            {"title": "MAILBAG", "note": "Troop meetings and the Scoutmaster's role, part 1", "groups": [3]},
            # Group 4 (outro) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    29: {
        "title":   "Troop meetings and planning ahead, part 2",
        "summary": "Clark Green continues the troop meetings series, using the story of a painter's chaotic-looking studio as a metaphor for the productive disorder of a well-run Scout meeting—where what looks like a mess is actually Scouts learning. Also continues the series on planning the future of your unit.",
        "tags":    ["troop-meetings", "scoutmaster-role", "youth-leadership", "unit-planning"],
        "sections": [
            {"title": "INTRO", "note": "Two kayakers in the cold: you can't have your kayak and heat it too", "groups": [0, 1]},
            {"title": "LISTENERS EMAIL", "note": "The artist's studio and the troop meeting — productive chaos", "groups": [2]},
            {"title": "MAILBAG", "note": "Future of your unit, part 3", "groups": [3]},
        ],
        "guests":   [],
        "segments": [],
    },

    30: {
        "title":   "Troop meetings and the future of your unit, part 4",
        "summary": "Recorded while at Algonquin Provincial Park in Ontario, Clark Green wraps up the troop meetings series with Baden-Powell's century-old advice about trusting patrol leaders and concludes the four-part series on planning the future of your Scout unit. Includes a Scoutmaster's Minute.",
        "tags":    ["troop-meetings", "unit-planning", "baden-powell", "patrol-leader", "high-adventure"],
        "sections": [
            {"title": "INTRO", "note": "How to make a million dollars in scouting: first get two million", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Recording from Algonquin Park, Ontario", "groups": [2]},
            {"title": "MAILBAG", "note": "Baden-Powell on trusting patrol leaders; troop meetings part 3", "groups": [3]},
            # Groups 4 (future of unit part 4), 5 (Scoutmaster's Minute), 6, 7, 8 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    31: {
        "title":   "Self-sufficient Scouts and the boy-led troop",
        "summary": "Back from summer camp and a canoe trip, Clark Green shares listener letters about troops that have become truly boy-led, including Larry Geiger's story of an Appalachian Trail hike where the Scouts cared for their adult leaders—not the other way around.",
        "tags":    ["boy-led-troop", "youth-leadership", "patrol-method", "summer-camp"],
        "sections": [
            {"title": "INTRO", "note": "Two penguins in a canoe crossing the Sahara Desert", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Larry Geiger and Steve B. on self-sufficient Scouts doing the whole thing themselves", "groups": [2]},
            # Groups 3, 4, 5 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    32: {
        "title":   "A model troop outing and merit badge counselors",
        "summary": "Clark Green describes the structure of a model Scout troop campout from preparation to execution, emphasizing the independence of youth leadership throughout. The episode also includes a quiz on merit badge counselors to test knowledge of the program's requirements.",
        "tags":    ["troop-outings", "patrol-method", "merit-badges", "youth-leadership"],
        "sections": [
            {"title": "INTRO", "note": "The brain store — a Scoutmaster brain costs $3 million", "groups": [0, 1]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "A model troop outing: adult and Scout roles", "groups": [2]},
            # Groups 3, 4 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    33: {
        "title":   "Den chiefs and a story from summer camp",
        "summary": "Clark Green discusses den chiefs as a valuable entry-level leadership position for older Scouts, featuring an interview with one of his Scouts about the role and its rewards. The episode also includes the return of the 'This Has Got to Be True' summer camp story segment.",
        "tags":    ["den-chief", "leadership-positions", "summer-camp", "cub-scouts", "patrol-method"],
        "sections": [
            {"title": "INTRO", "note": "Two bear biologists follow the sign: 'Bear Left'", "groups": [0, 1]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Den chiefs: entry-level leadership connecting Boy Scouts to Cub Scout dens", "groups": [2]},
            # Groups 3–7 (den chief interview + camp story), 8 (outro) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    37: {
        "title":   "Preparing for fall: parents meetings and adult training",
        "summary": "A shorter podcast recorded while preparing for a council training event, covering practical steps for the upcoming scouting year including parents meetings and upcoming interviews with long-time blog readers.",
        "tags":    ["parents-meeting", "adult-training", "troop-management", "unit-planning"],
        "sections": [
            {"title": "INTRO", "note": "Girl Scout navigation: in case they ever find themselves with a Boy Scout", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Preparing for fall: parents meetings, adult training, and upcoming interviews", "groups": [2]},
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
            {"title": "INTRO", "note": "Alaska grizzly bears on a ridge", "groups": [0]},
            {"title": "INTERVIEW", "note": "Larry Geiger, Scoutmaster, Cocoa FL — program, boy-led journey, and Scouts who lead themselves", "groups": [1]},
            # Group 2 (outro) — unnamed
        ],
        "guests":   ["Larry Geiger"],
        "segments": [],
    },

    39: {
        "title":   "Parents meetings, courts of honor, and ceremony",
        "summary": "Clark Green shares how he runs the annual parents meeting—including a Friends of Scouting presentation and group gear order through Campmore—then covers courts of honor and ceremony in Scouting, arguing for brevity, tradition, and meaning over florid theatrical displays.",
        "tags":    ["parents-meeting", "court-of-honor", "ceremony", "friends-of-scouting", "troop-management"],
        "sections": [
            {"title": "INTRO", "note": "How are Scoutmasters different from Sherlock Holmes? Holmes occasionally had a clue", "groups": [0, 1]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Parents meetings, Friends of Scouting, group gear orders, courts of honor, and ceremony", "groups": [2, 4, 5]},
            # Groups 3 (interstitial), outros — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    40: {
        "title":   "Interview: Working the Patrol Method (40th episode)",
        "summary": "A milestone 40th episode featuring a long interview with authors of the book Working the Patrol Method. Clark Green celebrates the occasion with listener thank-yous and digs into the patrol method with guests who have thought deeply about how it works in practice.",
        "tags":    ["patrol-method", "interview", "boy-led-troop", "youth-leadership"],
        "sections": [
            {"title": "INTRO", "note": "Two campaign hats go on a hike — worn out, went on ahead", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "40th episode celebration; reader thank-yous", "groups": [3]},
            # Group 2 (brief transition), outros — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    41: {
        "title":   "Mike Rowe's letter to an Eagle Scout",
        "summary": "Clark Green shares a letter Mike Rowe (host of Dirty Jobs) wrote to an Eagle Scout, which resonated widely in the scouting community, along with a comment from Colin who is on the home stretch to Eagle. The episode also features a Listeners Email segment.",
        "tags":    ["eagle-scout", "leadership-development", "youth-leadership", "scouting-values"],
        "sections": [
            {"title": "INTRO", "note": "The lumberjack who just couldn't cut it — they gave him the axe", "groups": [0, 1]},
            {"title": "LISTENERS EMAIL", "note": "Mike Rowe's letter to an Eagle Scout and Colin's response", "groups": [3]},
            # Groups 2 (interstitial), 4, 5, 6 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    42: {
        "title":   "Boys will be boys",
        "summary": "Clark Green introduces a quote from cartoonist Kin Hubbard—'Boys will be boys, and so will a lot of middle-aged men'—as a window into what Scout leaders know about themselves, then delivers a Scoutmastership in Seven Minutes segment on a topic relevant to that insight.",
        "tags":    ["scoutmastership", "leadership-development", "scout-leaders"],
        "sections": [
            {"title": "INTRO", "note": "Kin Hubbard: boys will be boys, and so will a lot of middle-aged men", "groups": [0, 1]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "", "groups": [3]},
            # Groups 2 (brief welcome), 4, 5, 6 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    43: {
        "title":   "When youth leadership works",
        "summary": "Clark Green shares a blog post by new Scoutmaster Brian Spellman of Fishers, Indiana, who describes the moment he truly saw his Scouts lead themselves. The episode explores what it looks and feels like when the patrol method actually works—and a listener email touches on similar themes.",
        "tags":    ["patrol-method", "youth-leadership", "boy-led-troop", "scoutmaster-stories"],
        "sections": [
            {"title": "INTRO", "note": "Things Scout leaders say that scouts hear differently: 'lights out, all quiet'", "groups": [0, 1]},
            {"title": "LISTENERS EMAIL", "note": "Scoutmaster Brian Spellman on the moment he saw youth leadership actually work", "groups": [2]},
            {"title": "MAILBAG", "note": "Listener letters on the patrol method and youth leadership", "groups": [3]},
            # Groups 4, 5, 6 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    44: {
        "title":   "Adventure, planning, and patrol leader elections",
        "summary": "Clark Green reflects on Roald Amundsen's famous observation that adventure is just bad planning brought to light by trial, then responds to listener feedback on patrol leader elections from the previous episode.",
        "tags":    ["patrol-leader", "leadership-elections", "advancement", "adventure"],
        "sections": [
            {"title": "INTRO", "note": "Roald Amundsen: an adventure is merely a bit of bad planning", "groups": [0, 1]},
            {"title": "LISTENERS EMAIL", "note": "Listener feedback on patrol leader elections and youth leadership", "groups": [2]},
            # Groups 3, 4, 5 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    45: {
        "title":   "Boards of review",
        "summary": "Clark Green discusses how boards of review should be conducted and provides resources for training board members—emphasizing they are not retests of scout skills but meaningful conversations. The episode also marks the blog's fifth anniversary and discusses how to support the podcast and blog.",
        "tags":    ["boards-of-review", "advancement", "troop-management", "eagle-scout"],
        "sections": [
            {"title": "INTRO", "note": "Lost economists: according to the map, we're standing on top of that mountain", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Boards of review — how to run them and train board members; blog's 5th anniversary", "groups": [2]},
            # Groups 3, 4 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    46: {
        "title":   "The scouting process",
        "summary": "Clark Green explains why Scouting is fundamentally a process—not a production line—and why liberating yourself from the need for measurable outputs is essential to understanding the mission. A Scoutmaster's Minute uses the metaphor of a Scout shirt to describe the Scouting program to non-Scout audiences.",
        "tags":    ["scoutmastership", "scouting-values", "youth-leadership", "scout-oath", "patrol-method"],
        "sections": [
            {"title": "INTRO", "note": "If you think it goes without saying, it almost certainly does not", "groups": [0, 1]},
            {"title": "SCOUTMASTERSHIP IN 7 MINUTES", "note": "Scouting as a process, not a product — the mission is preparation, not production", "groups": [2]},
            {"title": "SCOUTMASTER'S MINUTE", "note": "The Scout shirt as a metaphor for the Scouting program", "groups": [3]},
            # Groups 4, 5 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    47: {
        "title":   "When scouting works and listener email",
        "summary": "Clark Green shares a listener letter from Larry Geiger that perfectly captures when Scouting is working: 'Scouts don't behave like a product.' The episode also covers a Listeners Email segment on recognizing the moment a Scout has genuinely grown.",
        "tags":    ["scoutmastership", "youth-leadership", "scouting-values", "patrol-method"],
        "sections": [
            {"title": "INTRO", "note": "Evidence Santa Claus might be a Scoutmaster", "groups": [0, 1]},
            {"title": "LISTENERS EMAIL", "note": "Larry Geiger: 'Scouts don't behave like a product' — you'll know it's working when a mom asks, what happened to my little boy?", "groups": [2]},
        ],
        "guests":   [],
        "segments": [],
    },

    48: {
        "title":   "Listener questions and mailbag",
        "summary": "Clark Green reads letters from listeners including Ray from Oak Ridge, Tennessee, then digs into two listener questions about troop management and Scouting practice.",
        "tags":    ["troop-management", "listener-questions", "scouting-advice"],
        "sections": [
            {"title": "INTRO", "note": "Scoutmaster goes to his final reward and meets the devil", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Ray (Oak Ridge TN) and listener letters on the podcast", "groups": [2]},
            {"title": "MAILBAG", "note": "Listener questions on troop management", "groups": [3]},
            # Groups 4, 5 (outros) — unnamed
        ],
        "guests":   [],
        "segments": [],
    },

    49: {
        "title":   "Mailbag and the patrol method filmstrip",
        "summary": "Clark Green reads listener mail including a review from Skater Brian on iTunes, then shares the audio from a vintage patrol method filmstrip—a relic from the BSA's past that still has plenty to say about the core of Scout leadership.",
        "tags":    ["patrol-method", "listener-questions", "mailbag", "scouting-history"],
        "sections": [
            {"title": "INTRO", "note": "You know why they didn't make two Yogi Bears? They tried, but somebody made a boo-boo", "groups": [0, 1]},
            {"title": "MAILBAG", "note": "Skater Brian (iTunes) and Troop 237 listener letters", "groups": [2]},
            {"title": "MAILBAG", "note": "The patrol method filmstrip audio and listener responses", "groups": [3]},
        ],
        "guests":   [],
        "segments": [],
    },

    50: {
        "title":   "50th episode celebration",
        "summary": "A special milestone 50th episode with listener thank-yous from iTunes and Larry Geiger, plus the announcement of a monthly Scoutmaster newsletter to be sent to subscribers. Clark reflects on reaching 50 episodes and what the podcast has meant.",
        "tags":    ["milestone", "newsletter", "listener-community", "scouting-values"],
        "sections": [
            {"title": "INTRO", "note": "Three pieces of string want milkshakes — one ties himself in a knot and frays his hair", "groups": [0, 1]},
            # Groups 2, 3, 4 (listener thank-yous and outro) — unnamed
        ],
        "guests":   [],
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
    groups = []
    if not entries:
        return groups
    cs, ct, pe = entries[0][0], [entries[0][2]], entries[0][1]
    for s, e, t in entries[1:]:
        if s - pe > gap:
            groups.append((cs, " ".join(ct)))
            cs, ct = s, [t]
        else:
            ct.append(t)
        pe = e
    if ct:
        groups.append((cs, " ".join(ct)))
    return groups


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
        first_g = sec["groups"][0]
        start_s = groups[first_g][0]
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
    for i, (start_s, text) in enumerate(groups):
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
    tag_lines    = "tags:\n" + "\n".join(f'  - "{t}"' for t in tags) + "\n"
    safe_summary = summary.replace('"', "'").replace('\n', ' ')[:400]
    return fm_body + tag_lines + f'summary: "{safe_summary}"\n'


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
        section_first_g[id(sec)] = sec["groups"][0]
        for g in sec["groups"]:
            group_section[g] = sec

    lines = []
    for i, (start_s, text) in enumerate(groups):
        sec = group_section.get(i)

        if sec is not None and i == section_first_g[id(sec)]:
            listen_url = f"{ep_page}?t={int(start_s)}"
            note       = sec.get("note", "")
            note_html  = (
                f'<span class="smcg-tp-note">{html_esc(note)}</span>' if note else ""
            )
            lines.append('<hr class="smcg-tp-rule">')
            lines.append(
                f'<div class="smcg-tp-hdr">'
                f'<span class="smcg-tp-label">{html_esc(sec["title"])}</span>'
                f'{note_html}'
                f'<a href="{listen_url}" class="smcg-tp-listen">&#9654; Listen</a>'
                f'</div>'
            )

        lines.append(f'<p>{html_esc(text)}</p>')

    safe_title    = ep_title.replace('"', "'")
    safe_subtitle = subtitle.replace('"', "'")
    transcript_url = f"{ep_page}transcript/"

    frontmatter = (
        "---\n"
        f'title: "Transcript — {safe_title}"\n'
        f'episode_title: "{safe_title}"\n'
        f'subtitle: "{safe_subtitle}"\n'
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
        for g in sec["groups"]:
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

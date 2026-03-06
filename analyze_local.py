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

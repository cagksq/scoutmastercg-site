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
    (re.compile(r'\bWeevilos\b',             re.IGNORECASE), 'Webelos'),
    (re.compile(r'\bScout\s+Mastership\b',   re.IGNORECASE), 'Scoutmastership'),
    (re.compile(r'\bScoutmaster\s+Ship\b',   re.IGNORECASE), 'Scoutmastership'),
    (re.compile(r'\bScout\s+Masters\b',      re.IGNORECASE), 'Scoutmasters'),
    (re.compile(r'\bScout\s+Master\b',       re.IGNORECASE), 'Scoutmaster'),
    # Host name spelling
    (re.compile(r'\bClark\s+Green\b'),                        'Clarke Green'),
    (re.compile(r'\bGeene\b'),                                 'Green'),
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
    # EP6 transcription error
    (re.compile(r'\bmoccasin telegram\b', re.IGNORECASE), 'moccasin telegraph'),
    # EP6 musical filler — Whisper gibberish between moccasin telegraph and adult-to-youth section
    (re.compile(r"And then we,?\s+as someone who cracks.*?will help them\.?\s*", re.IGNORECASE | re.DOTALL), ''),
    (re.compile(r"Treat\s+Susanne\s+Framinski\s+on\s+iTunes\.?\s*", re.IGNORECASE), ''),
    # LISTENERS EMAIL / MAILBAG jingle — "Write me a letter, send it by mail..."
    (re.compile(
        r"Write\s+me\s+a\s+letter.*?(?:answer\s+to\s+one\s+of\s+your\s+emails?\.?\s*)",
        re.IGNORECASE | re.DOTALL), ''),
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
STANDARD_SECTIONS = {"INTRO", "MAILBAG", "WELCOME", "LISTENERS EMAIL"}

# sections: list of dicts describing named section breaks.
#   title  — displayed in the Sections index and as a header in the transcript
#   note   — optional subtitle (e.g. joke description, sender names)
#   groups — list of 0-based group indices covered by this section
# Groups not listed in any section appear in the transcript with a plain timestamp only.
_ANALYSIS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analysis.json")
with open(_ANALYSIS_PATH, encoding="utf-8") as _f:
    import json as _json
    ANALYSIS = {int(k): v for k, v in _json.load(_f).items()}



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
                          min_chars=PARA_MIN_CHARS, max_chars=PARA_MAX_CHARS,
                          force_breaks=None):
    """Split a group's raw SRT entries into paragraphs.

    Breaks at pauses >= para_gap seconds that follow a complete sentence,
    provided at least min_chars have accumulated (prevents single-sentence
    fragments).  Once max_chars are accumulated any sentence-end pause
    >= 0.4s triggers a break, preventing walls of text.
    force_breaks: list of timestamps (seconds) where a break is forced before
    any entry whose start time crosses the boundary — used to align paragraph
    starts with section seek_to timestamps.
    Returns list of (start_s, text) tuples.
    """
    if not raw_entries:
        return []
    force_breaks = sorted(force_breaks or [])
    paras = []
    para_start = raw_entries[0][0]
    para_texts = [raw_entries[0][2]]
    prev_end   = raw_entries[0][1]
    for s, e, t in raw_entries[1:]:
        gap = s - prev_end
        accumulated = " ".join(para_texts)
        acc_len = len(accumulated)
        at_sentence_end = bool(re.search(r'[.?!]["\']?\s*$', accumulated.rstrip()))
        forced = any(para_start < fb <= s for fb in force_breaks)
        should_break = forced or (at_sentence_end and (
            (gap >= para_gap and acc_len >= min_chars) or
            (gap >= 0.4     and acc_len >= max_chars)
        ))
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


def split_into_emails(raw_entries, email_gap=EMAIL_GAP, force_breaks=None):
    """For MAILBAG / LISTENERS EMAIL groups: split raw entries into individual
    emails, each returned as a list of (start_s, text) paragraph tuples.

    An email boundary is a gap >= email_gap seconds that follows a sentence end.
    force_breaks (list of seconds) are passed through to split_into_paragraphs
    so that seek_to timestamps (e.g. OUTRO) create clean paragraph splits.
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
            emails.append(split_into_paragraphs(current, force_breaks=force_breaks))
            current = [(s, e, t)]
        else:
            current.append((s, e, t))
        prev_end = e
    if current:
        emails.append(split_into_paragraphs(current, force_breaks=force_breaks))
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
        if "seek_to" in sec:
            start_s = sec["seek_to"]
        elif sec.get("groups"):
            start_s = groups[sec["groups"][0]][0]
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


def update_frontmatter(fm_body, tags, summary, title, ep_num=None):
    # Reset page title to "Scoutmaster Podcast N" (strip any old subtitle appended to it)
    if ep_num:
        fm_body = re.sub(r'^title:.*\n', f'title: "Scoutmaster Podcast {ep_num}"\n', fm_body, flags=re.MULTILINE)
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
    # First pass: all non-OUTRO sections claim their groups.
    # Boundary sections (no seek_to) take priority over mid-group sections (seek_to)
    # so that WELCOME is never overwritten by e.g. SCOUTMASTERSHIP sharing the same group.
    for sec in sections:
        if not sec.get("groups") or sec["title"] == "OUTRO":
            continue  # seek_to-only or OUTRO — handled below / injected mid-group
        section_first_g[id(sec)] = sec["groups"][0]
        for g in sec["groups"]:
            existing = group_section.get(g)
            if existing is None or ("seek_to" in existing and "seek_to" not in sec):
                group_section[g] = sec
    # Second pass: OUTRO only claims groups not already owned by another section
    # (prevents OUTRO from silently eating a shared group and suppressing its content)
    for sec in sections:
        if not sec.get("groups") or sec["title"] != "OUTRO":
            continue
        section_first_g[id(sec)] = sec["groups"][0]
        for g in sec["groups"]:
            if g not in group_section:
                group_section[g] = sec

    # sections with seek_to sorted by timestamp — injected between paragraphs at seek_to point
    # (includes sections that also have groups — header fires at seek_to, not at group boundary)
    seekt_sections = sorted(
        [s for s in sections if "seek_to" in s],
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

        # suppress group-boundary header if section has seek_to — it fires via seekt_sections instead
        if sec is not None and i == section_first_g[id(sec)] and "seek_to" not in sec:
            lines.append('<hr class="smcg-tp-rule">')
            lines.append(render_tp_hdr(sec, start_s))

        # seek_to sections whose timestamp falls within this group
        group_end = groups[i + 1][0] if i + 1 < len(groups) else float("inf")
        pending   = [s for s in seekt_sections if start_s <= s["seek_to"] < group_end]
        injected  = set()

        def maybe_inject(para_start, para_end=float("inf")):
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
            force_breaks = [s["seek_to"] for s in pending]
            emails = split_into_emails(raw_entries, force_breaks=force_breaks)
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
                    if pi == 0 and sec_title == "MAILBAG":
                        lines.append(f'<p class="smcg-tp-from">{html_esc(para_text)}</p>')
                    else:
                        lines.append(f'<p>{html_esc(para_text)}</p>')
        else:
            force_breaks = [s["seek_to"] for s in pending]
            paras = split_into_paragraphs(raw_entries, force_breaks=force_breaks)
            for pi, (para_start, para_text) in enumerate(paras):
                para_end = paras[pi + 1][0] if pi + 1 < len(paras) else group_end
                maybe_inject(para_start, para_end)
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

    # Write HTML to a data file so goldmark never sees it.
    # Hugo's go-yaml parser silently fails on large YAML block scalars;
    # JSON data files bypass frontmatter parsing entirely.
    import json as _json
    data_dir = os.path.join(os.path.dirname(__file__), "data", "transcripts")
    os.makedirs(data_dir, exist_ok=True)
    data_path = os.path.join(data_dir, f"episode-{ep_num}.json")
    with open(data_path, "w", encoding="utf-8") as df:
        _json.dump({"html": "\n".join(lines)}, df, ensure_ascii=False)

    frontmatter = (
        "---\n"
        f'title: "Transcript — {safe_title}"\n'
        f'episode_title: "{safe_title}"\n'
        f'subtitle: "{safe_subtitle}"\n'
        f'description: "Transcript of {safe_title} — {safe_desc}"\n'
        f'summary: "Transcript of {safe_title} — {safe_desc}"\n'
        f'episode_url: "{ep_page}"\n'
        f'url: "{transcript_url}"\n'
        f'episode: {ep_num}\n'
        "draft: false\n"
        "---\n"
    )
    return frontmatter + "\n"


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

    # Subtitle: use explicit key if present (set by AI or manual override),
    # otherwise fall back to longest note from instructional sections,
    # avoiding story sections unless nothing else is available.
    STORY_SECTIONS = {"THIS HAS TO BE THE TRUTH", "STORY FROM CAMP"}
    if data.get("subtitle"):
        subtitle = data["subtitle"]
    else:
        feature_secs = [s for s in sections if s["title"] not in STANDARD_SECTIONS and s.get("note")]
        instructional = [s for s in feature_secs if s["title"] not in STORY_SECTIONS]
        pool = instructional if instructional else feature_secs
        subtitle = max(pool, key=lambda s: len(s["note"]))["note"] if pool else data.get("title", "")
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

    fm_body  = update_frontmatter(fm_body, data["tags"], data["summary"], subtitle, ep_num)
    new_body = body.rstrip() + "\n" + build_body_addition(section_index, ep_num)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(fm_open + fm_body + fm_close + new_body)

    print(f"  Saved: {md_path}")
    return True


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    # Status report: python3 analyze_local.py --status
    if len(sys.argv) == 2 and sys.argv[1] == "--status":
        import os as _os
        srt_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "TRANSCRIPTS")
        srt_eps = {int(re.sub(r'\D', '', f)) for f in _os.listdir(srt_dir) if f.endswith('.srt')}
        all_eps = sorted(set(ANALYSIS.keys()) | srt_eps | set(range(1, max(max(ANALYSIS.keys()), max(srt_eps) if srt_eps else 0) + 1)))
        completed   = [ep for ep in all_eps if ANALYSIS.get(ep, {}).get("status") == "completed"]
        in_process  = [ep for ep in all_eps if ANALYSIS.get(ep, {}).get("status") == "in_process"]
        transcribed = [ep for ep in all_eps if ep in srt_eps and ep not in ANALYSIS]
        untranscribed = [ep for ep in all_eps if ep not in srt_eps and ep not in ANALYSIS]
        def fmt(lst): return " ".join(str(e) for e in lst) or "(none)"
        print(f"COMPLETED   ({len(completed)}): {fmt(completed)}")
        print(f"IN PROCESS  ({len(in_process)}): {fmt(in_process)}")
        print(f"UNTRANSCRIBED ({len(untranscribed)} shown up to EP{max(all_eps)}): {fmt(untranscribed[:30])}{'...' if len(untranscribed)>30 else ''}")
        sys.exit(0)

    explicit = len(sys.argv) > 1
    if explicit:
        episodes = [int(a) for a in sys.argv[1:]]
    else:
        # Default run: only in_process episodes (skip completed)
        episodes = sorted(
            ep for ep, data in ANALYSIS.items()
            if data.get("status", "in_process") != "completed"
        )

    processed = skipped = errors = 0
    for ep in episodes:
        status = ANALYSIS.get(ep, {}).get("status", "in_process")
        if status == "completed" and explicit:
            print(f"[EP{ep:03d}] Skipping — marked completed (edit analysis.json to re-run)")
            skipped += 1
            continue
        result = process_episode(ep)
        if result is True:    processed += 1
        elif result is False: errors    += 1
        else:                 skipped   += 1

    print(f"\nDone.  Processed: {processed}  Skipped: {skipped}  Errors: {errors}")

#!/usr/bin/env python3
"""
Auto-detect section structure for Scoutmaster Podcast episodes.
Scans all SRT files not yet in analyze_local.py ANALYSIS dict.
Outputs ready-to-paste Python dict entries — fill in TODO notes, then add to ANALYSIS.

Run from the Hugo site root:
  python3 auto_detect.py
  python3 auto_detect.py 21 33    # specific range
"""

import os, re, sys, textwrap

TRANSCRIPTS_DIR = "transcripts"

# ── Import existing ANALYSIS to skip already-done episodes ────────────────────
try:
    from analyze_local import ANALYSIS, parse_srt, group_entries, fmt_time, GAP_THRESHOLD
    DONE = set(ANALYSIS.keys())
except ImportError:
    DONE = set()
    def parse_srt(p):
        with open(p) as f: content = f.read()
        entries = []
        for block in re.split(r'\n\s*\n', content.strip()):
            lines = [l for l in block.strip().splitlines() if l.strip()]
            for i, line in enumerate(lines):
                m = re.match(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)', line)
                if m:
                    s = int(m.group(1))*3600+int(m.group(2))*60+int(m.group(3))
                    e = int(m.group(5))*3600+int(m.group(6))*60+int(m.group(7))
                    entries.append((s, e, " ".join(lines[i+1:]))); break
        return entries
    def group_entries(entries, gap=4.0):
        groups = []
        if not entries: return groups
        cs, ct, pe = entries[0][0], [entries[0][2]], entries[0][1]
        for s, e, t in entries[1:]:
            if s - pe > gap: groups.append((cs, " ".join(ct))); cs, ct = s, [t]
            else: ct.append(t)
            pe = e
        if ct: groups.append((cs, " ".join(ct)))
        return groups
    def fmt_time(s):
        s=int(s); h=s//3600; m=(s%3600)//60; sec=s%60
        return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

# ── Trigger phrase tables ──────────────────────────────────────────────────────

NAMED_TRIGGERS = [
    # (section_title, [phrases_to_match])
    ("SCOUTMASTERSHIP IN 7 MINUTES", [
        "scoutmastership in seven minutes",
        "scoutmastership in 7 minutes",
        "scoutmastering in seven minutes",
    ]),
    ("LISTENERS EMAIL", [
        "email that is folks",
        "here's an answer to one of your email",
        "answer to one of your emails",
        "and here's an answer to",
        "that is folks and here",
    ]),
    ("SCOUTMASTER PANEL DISCUSSION", [
        "time for another scoutmaster panel",
        "scoutmaster panel discussion",
        "panel of scoutmasters",
    ]),
]

FEATURE_TRIGGERS = [
    "so let's get started, shall we",
    "so let's get started shall we",
    "let's get started, shall we",
    "well let's get started",
]

# Mailbag indicators
MAILBAG_TRIGGERS = [
    "troop ", "pack ", "crew ",
    "sends in", "writes in", "wrote in",
    "from the mailbag",
    "thanks for writing",
    "thanks for the email",
    "thanks for your email",
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def first_sentences(text, n=2, maxlen=120):
    """Return first n sentences of text, truncated to maxlen chars."""
    text = re.sub(r'\s+', ' ', text).strip()
    sents = re.split(r'(?<=[.!?])\s+', text)
    out = " ".join(sents[:n])
    if len(out) > maxlen:
        out = out[:maxlen].rsplit(' ', 1)[0] + "…"
    return out

def extract_mailbag_names(text):
    """Try to pull names + troop info from mailbag text."""
    # Pattern: Name (Troop/Pack/Crew NNN, City ST)
    hits = re.findall(
        r'([A-Z][a-z]+(?: [A-Z][a-z]+){0,2})'
        r'(?:[,\s]+(?:Troop|Pack|Crew)\s*\d+)?',
        text
    )
    names = []
    for h in hits:
        n = h[0].strip() if isinstance(h, tuple) else h.strip()
        if len(n) > 3 and n not in names:
            names.append(n)
    # Also grab "Troop NNN, City" snippets
    troops = re.findall(r'(?:Troop|Pack|Crew)\s*\d+(?:,\s*[A-Za-z ]+)?', text)
    if names and troops:
        return names[0] + (f" ({troops[0]})" if troops else "")
    return ", ".join(names[:3]) if names else ""

def detect_sections(groups):
    """Return list of detected section dicts (title, note, groups)."""
    used = set()
    sections = []

    # INTRO: always groups 0 and 1 (theme + joke)
    intro_groups = [0] if len(groups) == 1 else [0, 1]
    for g in intro_groups:
        used.add(g)
    joke_text = groups[1][1] if len(groups) > 1 else groups[0][1]
    # Try to pull just the punchline (last sentence)
    sents = re.split(r'(?<=[.!?])\s+', joke_text.strip())
    joke_note = sents[-1].strip() if sents else first_sentences(joke_text, 1)
    if len(joke_note) > 100:
        joke_note = "TODO: joke description"
    sections.append({"title": "INTRO", "note": joke_note, "groups": list(intro_groups)})

    # Scan remaining groups for named sections and features
    for i, (start_s, text, *_) in enumerate(groups):
        if i in used:
            continue
        tl = text.lower()

        # Named section triggers
        matched = False
        for title, phrases in NAMED_TRIGGERS:
            if any(p in tl for p in phrases):
                sections.append({"title": title, "note": "", "groups": [i]})
                used.add(i)
                matched = True
                break
        if matched:
            continue

        # Mailbag detection (group 2 or 3 usually)
        if i in (2, 3) and any(p in tl for p in MAILBAG_TRIGGERS):
            note = extract_mailbag_names(text) or "TODO: sender names"
            sections.append({"title": "MAILBAG", "note": note, "groups": [i]})
            used.add(i)
            continue

        # Feature trigger
        if any(p in tl for p in FEATURE_TRIGGERS):
            note = first_sentences(text, 2, 150) or "TODO: feature description"
            sections.append({
                "title": "TODO: FEATURE TITLE",
                "note": note,
                "groups": [i],
                "_auto": True,
            })
            used.add(i)

    return sections

def format_analysis_entry(ep_num, groups, sections):
    """Return a formatted Python dict string ready to paste into ANALYSIS."""
    lines = [f"    {ep_num}: {{"]
    lines.append(f'        "title":   "TODO: episode title",')
    lines.append(f'        "summary": "TODO: summary",')
    lines.append(f'        "tags":    [],')
    lines.append(f'        "sections": [')

    for sec in sections:
        title = sec["title"]
        note  = sec.get("note", "").replace('"', "'")
        grps  = sec["groups"]
        times = [fmt_time(groups[g][0]) for g in grps if g < len(groups)]
        auto  = " ← AUTO" if sec.get("_auto") else ""
        lines.append(f'            {{"title": "{title}", "note": "{note}", "groups": {grps}}},  # {", ".join(times)}{auto}')

    # List unassigned groups as comments
    assigned = set(g for s in sections for g in s["groups"])
    unassigned = [i for i in range(len(groups)) if i not in assigned]
    if unassigned:
        lines.append(f'            # Unassigned groups: {unassigned}')
        for i in unassigned:
            lines.append(f'            # [{i}] {fmt_time(groups[i][0])} — {first_sentences(groups[i][1], 1, 80)}')

    lines.append(f'        ],')
    lines.append(f'        "guests":   [],')
    lines.append(f'        "segments": [],')
    lines.append(f'    }},')
    return "\n".join(lines)

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    start_ep = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    end_ep   = int(sys.argv[2]) if len(sys.argv) > 2 else 999

    srt_files = {}
    for fname in os.listdir(TRANSCRIPTS_DIR):
        m = re.match(r'scoutmaster-podcast-(\d+)\.srt$', fname)
        if m:
            n = int(m.group(1))
            if start_ep <= n <= end_ep and n not in DONE:
                srt_files[n] = os.path.join(TRANSCRIPTS_DIR, fname)

    if not srt_files:
        print("No new episodes to process.")
        return

    print(f"# Auto-detected sections for {len(srt_files)} episode(s)")
    print(f"# Episodes already in ANALYSIS: {sorted(DONE)}\n")
    print("# ── Paste into ANALYSIS in analyze_local.py ──────────────────\n")

    for ep_num in sorted(srt_files):
        srt_path = srt_files[ep_num]
        entries  = parse_srt(srt_path)
        groups   = group_entries(entries)
        sections = detect_sections(groups)

        todo_count = sum(1 for s in sections if "TODO" in s.get("title", "") or "TODO" in s.get("note", ""))
        flag = f"  ← {todo_count} TODO(s)" if todo_count else ""

        print(f"    # EP{ep_num:03d} — {len(groups)} groups: {[fmt_time(g[0]) for g in groups]}{flag}")
        print(format_analysis_entry(ep_num, groups, sections))
        print()

if __name__ == "__main__":
    main()

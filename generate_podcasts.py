#!/usr/bin/env python3
"""
Generate Hugo podcast content pages from wayback export txt files.
"""

import os
import re
import glob
from datetime import datetime

POSTS_DIR = "/Users/clarkegreen 1/Downloads/wayback-export/outputs/posts"
OUTPUT_DIR = "/Users/clarkegreen 1/mysite/content/podcasts"
DEST_DIR = "/Users/clarkegreen 1/mysite/static/audio"

# MP3 source folders
MP3_FOLDERS = [
    "/Volumes/ RAID/SMCG/SMCG Podcast/Podcact Archives/1-100",
    "/Volumes/ RAID/SMCG/SMCG Podcast/Podcact Archives/101-200",
    "/Volumes/ RAID/SMCG/SMCG Podcast/Podcact Archives/201-300",
    "/Volumes/ RAID/SMCG/SMCG Podcast/Podcact Archives/301-400",
]

os.makedirs(OUTPUT_DIR, exist_ok=True)


def find_mp3(episode_num):
    """Find the best MP3 file for a given episode number."""
    for folder in MP3_FOLDERS:
        # Try standard name first
        candidate = os.path.join(folder, f"ScoutmasterPodcast{episode_num}.mp3")
        if os.path.exists(candidate):
            return candidate
        # Try lowercase
        candidate = os.path.join(folder, f"Scoutmasterpodcast{episode_num}.mp3")
        if os.path.exists(candidate):
            return candidate
        # Try alternate prefix
        candidate = os.path.join(folder, f"RMScoutmasterPodcast{episode_num}.mp3")
        if os.path.exists(candidate):
            return candidate
    return None


def parse_date(text):
    """Try to extract a date from the post content."""
    # Patterns like "November 14, 2011" or "April 11, 2011"
    months = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    m = re.search(rf"{months}\s+\d{{1,2}},\s+\d{{4}}", text)
    if m:
        try:
            return datetime.strptime(m.group(0), "%B %d, %Y").strftime("%Y-%m-%d")
        except:
            pass
    # Fall back to filename date (YYYYMMDD)
    return None


def parse_episode_num(filename, content):
    """Extract episode number from filename or content."""
    # From filename: 20110402_Scoutmaster_Podcast_58_-_Les_Stroud.txt
    m = re.search(r'[Pp]odcast[_\s]+(\d+)', filename)
    if m:
        return int(m.group(1))
    # From content
    m = re.search(r'[Pp]odcast\s+(\d+)', content)
    if m:
        return int(m.group(1))
    return None


def parse_description(lines):
    """Extract description content, handling both early and late episode formats."""

    # Lines that mark the end of useful content
    stop_phrases = (
        "Podcast:", "Podcast Notes", "Links in this Podcast:",
        "Sponsored By", "Subscribe:", "Listen to this episode",
        "Get updates to Scoutmastercg.com",
    )
    # Lines to skip over (boilerplate)
    skip_phrases = {
        "Play in new window", "Download", "Subscribe on iTunes",
        "Podcast Music", "null", "Subscribe to the Scoutmaster Newsletter",
        "In this Podcast:", "|", "iTunes", "Android", "RSS",
        "Was this information Useful? Tell your friends!",
        "PODCAST ARCHIVE", "Past editions of the show are available at the",
        "Four Percent", "Available as a hard cover book",
        "Podcast Music", "Leave a Comment", "Uncategorized", "·",
        ")", "(", "Scoutmaster Podcast",
    }
    # Header lines to skip before content begins
    header_skip = (
        "by", "on", "in", "clarke green", "podcast", "comments",
    )
    # Bio sentinels — stop collecting
    bio_sentinels = (
        "at Scoutmastercg.com",
        "Kennett Square",
        "wife Teddi",
        "The Scouting Journey",
        "Thoughts on Scouting",
        "scoutmastercg.com,",
    )

    # Phase 1: find where the real content starts
    # Skip: title (line 0), blank, URLs (lines 2-3), blank, title-repeat,
    # date, by/on/in, author name, N Comments, category
    # Content starts after all that header boilerplate.
    # Strategy: skip lines until we've passed the date line, then collect.

    past_header = False
    date_seen = False
    desc_lines = []

    import re as _re
    date_pat = _re.compile(
        r'(January|February|March|April|May|June|July|August|'
        r'September|October|November|December)\s+\d{1,2},\s+\d{4}'
    )

    for i, line in enumerate(lines):
        # Skip the first 5 lines (title, blank, URLs, blank)
        if i < 5:
            continue

        stripped = line.strip()
        normalized = stripped.replace('\xa0', ' ').replace('\u2019', "'")

        # Detect date line
        if date_pat.search(stripped):
            date_seen = True
            continue

        # Skip header boilerplate after date
        if not past_header:
            if date_seen and normalized.lower() in header_skip:
                continue
            if date_seen and _re.match(r'^\d+\s+[Cc]omments?$', normalized):
                continue
            if date_seen and normalized.lower() == "clarke green":
                continue
            # Once we've seen the date and hit a non-header line, we're in content
            if date_seen and normalized and normalized.lower() not in header_skip:
                past_header = True

        if not past_header:
            continue

        # Stop at boilerplate terminators
        if any(normalized.startswith(p) or normalized == p for p in stop_phrases):
            break

        # Stop at bio
        if any(sentinel.lower() in normalized.lower() for sentinel in bio_sentinels):
            break

        # Skip individual boilerplate lines
        if normalized in skip_phrases or any(normalized.startswith(p) for p in skip_phrases):
            continue

        if not normalized:
            if desc_lines:
                desc_lines.append("")
            continue

        # Skip lines that are just the title repeated
        if normalized == lines[0].strip():
            continue

        desc_lines.append(normalized)

    # Trim trailing blank lines
    while desc_lines and not desc_lines[-1]:
        desc_lines.pop()
    return "\n".join(desc_lines)


def title_from_url(url):
    """Derive a readable title from a URL slug."""
    # Strip protocol, domain, query string
    slug = re.sub(r'https?://[^/]+/', '', url)
    slug = slug.split('?')[0].strip('/')
    # Convert hyphens to spaces and title-case
    title = slug.replace('-', ' ').replace('_', ' ').title()
    return title or None


def process_file(filepath):
    filename = os.path.basename(filepath)

    # Only process podcast posts
    if "podcast" not in filename.lower():
        return None

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    lines = content.splitlines()
    if not lines:
        return None

    title = lines[0].strip()
    if not title:
        return None

    # If first line is a URL, derive title from URL slug
    url_as_title = title.startswith("http")
    if url_as_title:
        title = title_from_url(title) or title

    # Get date from filename first, then content
    date_from_filename = None
    m = re.match(r"(\d{4})(\d{2})(\d{2})_", filename)
    if m:
        date_from_filename = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    date_from_content = parse_date(content)
    date = date_from_content or date_from_filename or "2011-01-01"

    episode_num = parse_episode_num(filename, content)
    description = parse_description(lines)

    mp3_path = find_mp3(episode_num) if episode_num else None
    audio_file = f"/audio/ScoutmasterPodcast{episode_num}.mp3" if episode_num else ""

    return {
        "title": title,
        "date": date,
        "episode": episode_num,
        "description": description,
        "audio_file": audio_file,
        "mp3_source": mp3_path,
        "url_as_title": url_as_title,
    }


def slug_from_title(title, episode):
    s = title.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    if episode:
        return f"episode-{episode}"
    return s[:60]


def write_markdown(data):
    episode = data["episode"]
    slug = slug_from_title(data["title"], episode)
    out_path = os.path.join(OUTPUT_DIR, f"{slug}.md")

    # Escape quotes in title
    title = data["title"].replace('"', '\\"')

    desc_block = ""
    if data["description"]:
        desc_block = f"\n{data['description']}\n"

    audio_block = ""
    if data["audio_file"]:
        audio_block = f'\n{{{{< audio src="{data["audio_file"]}" >}}}}\n'

    episode_line = f"episode: {episode}\n" if episode else ""

    md = f"""---
title: "{title}"
date: {data["date"]}
draft: false
{episode_line}categories: ["Podcast"]
---
{audio_block}{desc_block}"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    return out_path


# --- Main ---

# Only generate pages for episodes we have MP3s for
available_mp3s = set()
for f in os.listdir(DEST_DIR):
    m = re.search(r'[Pp]odcast(\d+)\.mp3$', f)
    if m:
        available_mp3s.add(int(m.group(1)))

print(f"MP3 files available: {len(available_mp3s)}")

txt_files = sorted(glob.glob(os.path.join(POSTS_DIR, "*.txt")))
podcast_files = [f for f in txt_files if "podcast" in os.path.basename(f).lower()]

print(f"Found {len(podcast_files)} podcast txt files")

# Clear existing podcast content pages
for f in glob.glob(os.path.join(OUTPUT_DIR, "*.md")):
    os.remove(f)

generated = 0
skipped = 0
seen_episodes = {}

for filepath in podcast_files:
    data = process_file(filepath)
    if not data:
        skipped += 1
        continue

    ep = data["episode"]

    # Skip entries without an episode number or without a matching MP3
    if not ep or ep not in available_mp3s:
        continue

    # De-duplicate: prefer proper title, then longer description
    if ep in seen_episodes:
        existing = seen_episodes[ep]
        if existing["url_as_title"] and not data["url_as_title"]:
            seen_episodes[ep] = data
        elif not existing["url_as_title"] and data["url_as_title"]:
            pass  # keep existing
        elif len(data["description"]) > len(existing["description"]):
            seen_episodes[ep] = data
        continue

    seen_episodes[ep] = data

# Write one page per episode
for ep, data in seen_episodes.items():
    write_markdown(data)
    generated += 1

print(f"Generated: {generated} pages")
print(f"Skipped:   {skipped} files")
print(f"Output:    {OUTPUT_DIR}")

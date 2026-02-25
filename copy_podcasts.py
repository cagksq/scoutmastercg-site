#!/usr/bin/env python3
"""
Copy the best MP3 for each episode into static/audio/
Priority: ScoutmasterPodcastNNN.mp3 > Scoutmasterpodcast NNN.mp3 > RMScoutmasterPodcastNNN.mp3
Skips: .wav files, " copy" files, oddly named files
"""

import os
import re
import shutil
import glob

MP3_FOLDERS = [
    "/Volumes/ RAID/SMCG/SMCG Podcast/Podcact Archives/1-100",
    "/Volumes/ RAID/SMCG/SMCG Podcast/Podcact Archives/101-200",
    "/Volumes/ RAID/SMCG/SMCG Podcast/Podcact Archives/201-300",
    "/Volumes/ RAID/SMCG/SMCG Podcast/Podcact Archives/301-400",
]

DEST_DIR = "/Users/clarkegreen 1/mysite/static/audio"
os.makedirs(DEST_DIR, exist_ok=True)

def find_best_mp3(episode_num):
    """Return the best source MP3 path for a given episode number."""
    candidates = [
        f"ScoutmasterPodcast{episode_num}.mp3",
        f"Scoutmasterpodcast{episode_num}.mp3",
        f"ScoutmasterPodcast {episode_num}.mp3",
        f"RMScoutmasterPodcast{episode_num}.mp3",
    ]
    for folder in MP3_FOLDERS:
        for name in candidates:
            path = os.path.join(folder, name)
            if os.path.exists(path):
                return path
    return None

def get_all_episodes():
    """Scan folders and collect all valid episode numbers."""
    episodes = set()
    for folder in MP3_FOLDERS:
        for f in os.listdir(folder):
            if f.endswith(".wav") or " copy" in f.lower():
                continue
            if not f.lower().endswith(".mp3"):
                continue
            m = re.search(r'[Pp]odcast\s*(\d+)', f)
            if m:
                episodes.add(int(m.group(1)))
    return sorted(episodes)

episodes = get_all_episodes()
print(f"Found {len(episodes)} unique episode numbers")

copied = 0
skipped = 0
missing = 0

for ep in episodes:
    dest = os.path.join(DEST_DIR, f"ScoutmasterPodcast{ep}.mp3")
    if os.path.exists(dest):
        skipped += 1
        continue

    src = find_best_mp3(ep)
    if not src:
        print(f"  MISSING: episode {ep}")
        missing += 1
        continue

    print(f"  Copying episode {ep}: {os.path.basename(src)}")
    shutil.copy2(src, dest)
    copied += 1

print(f"\nDone. Copied: {copied}  Already existed: {skipped}  Missing: {missing}")

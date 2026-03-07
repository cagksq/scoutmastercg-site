#!/usr/bin/env python3
"""
Transcribe Scoutmaster Podcast episodes using OpenAI Whisper.
Writes .srt and .txt files to transcripts/.
Resumable — skips episodes that already have an .srt file.

Run from the Hugo site root:
  cd "/Users/clarkegreen 1/mysite"
  python3 transcribe.py

To process a specific range:
  python3 transcribe.py 1 50
"""

import os
import sys
import urllib.request
import urllib.error
import tempfile
import whisper

TRANSCRIPTS_DIR = "TRANSCRIPTS"
LOCAL_AUDIO_DIR = "static/audio"
URL_BASE        = (
    "https://scoutmastercg-podcast.s3.us-east-005.backblazeb2.com/"
    "scoutmaster-podcast-{}.mp3"
)
MODEL_NAME = "turbo"
DEVICE     = "mps"   # Apple Silicon GPU — falls back to cpu if unavailable


def ms_to_srt(ms):
    h   = ms // 3_600_000
    m   = (ms % 3_600_000) // 60_000
    s   = (ms % 60_000) // 1_000
    ms_ = ms % 1_000
    return f"{h:02d}:{m:02d}:{s:02d},{ms_:03d}"


def write_srt(segments, path):
    with open(path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            start = int(seg["start"] * 1000)
            end   = int(seg["end"]   * 1000)
            text  = seg["text"].strip()
            f.write(f"{i}\n{ms_to_srt(start)} --> {ms_to_srt(end)}\n{text}\n\n")


def write_txt(segments, path):
    with open(path, "w", encoding="utf-8") as f:
        for seg in segments:
            f.write(seg["text"].strip() + "\n")


def url_exists(url):
    try:
        req = urllib.request.Request(url, method="HEAD")
        urllib.request.urlopen(req, timeout=10)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        return True   # other errors (timeouts etc) — try anyway
    except Exception:
        return False


def transcribe_episode(ep_num, model):
    label    = f"EP{ep_num:03d}"
    srt_path = os.path.join(TRANSCRIPTS_DIR, f"scoutmaster-podcast-{ep_num}.srt")
    txt_path = os.path.join(TRANSCRIPTS_DIR, f"scoutmaster-podcast-{ep_num}.txt")

    if os.path.exists(srt_path):
        print(f"[{label}] already transcribed — skipping")
        return "skip"

    # Try local file first, then S3
    local_path = os.path.join(LOCAL_AUDIO_DIR, f"ScoutmasterPodcast{ep_num}.mp3")
    use_local  = os.path.exists(local_path)

    if not use_local:
        url = URL_BASE.format(ep_num)
        if not url_exists(url):
            print(f"[{label}] audio not found locally or on S3 — skipping")
            return "skip"

    tmp_path = None
    try:
        if use_local:
            print(f"[{label}] using local file...", end=" ", flush=True)
            size_mb = os.path.getsize(local_path) / 1_048_576
            print(f"{size_mb:.1f} MB", flush=True)
            audio_path = local_path
        else:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
            print(f"[{label}] downloading...", end=" ", flush=True)
            urllib.request.urlretrieve(url, tmp_path)
            size_mb = os.path.getsize(tmp_path) / 1_048_576
            print(f"{size_mb:.1f} MB", flush=True)
            audio_path = tmp_path

        print(f"[{label}] transcribing...", end=" ", flush=True)
        result   = model.transcribe(audio_path, language="en", fp16=False)
        segments = result["segments"]
        write_srt(segments, srt_path)
        write_txt(segments, txt_path)
        print(f"{len(segments)} segments — done", flush=True)
        return "ok"

    except Exception as e:
        print(f"FAILED: {e}", flush=True)
        for p in [srt_path, txt_path]:
            if os.path.exists(p):
                os.unlink(p)
        return "fail"

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


if __name__ == "__main__":
    start_ep = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    end_ep   = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    episodes = list(range(start_ep, end_ep + 1))

    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

    print(f"Loading Whisper '{MODEL_NAME}' model on {DEVICE}...")
    try:
        model = whisper.load_model(MODEL_NAME, device=DEVICE)
    except Exception:
        print(f"  {DEVICE} failed, falling back to cpu")
        model = whisper.load_model(MODEL_NAME, device="cpu")
    print(f"Model loaded. Processing episodes {start_ep}–{end_ep}.\n")

    counts = {"ok": 0, "skip": 0, "fail": 0}
    for ep in episodes:
        counts[transcribe_episode(ep, model)] += 1

    print(f"\nDone.  Transcribed: {counts['ok']}  Skipped: {counts['skip']}  Failed: {counts['fail']}")
    print(f"SRT files written to: {TRANSCRIPTS_DIR}/")

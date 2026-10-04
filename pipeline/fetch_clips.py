#!/usr/bin/env python3
"""Fetch one short YouTube news clip per story.

Input:  work/segments.json  (needs "id" + "headline" per story)
Output: work/clip_<id>.mp4  (1080x1920, ~12s, no audio)

Uses yt-dlp with the android player client (bypasses YouTube bot checks
from datacenter IPs). Clips are trimmed from the middle of the video.
Stories with no usable clip are skipped -> compose.py falls back to image.
"""
import json, os, sys, subprocess

CLIP_LEN = 12  # seconds per clip

def run(cmd, timeout=180):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p

def search(query):
    """Return list of (id, title, duration) for a YouTube search."""
    p = run(["yt-dlp", "--no-check-certificate", "--extractor-args", "youtube:player_client=android",
             "--print", "%(id)s\t%(title)s\t%(duration)s",
             "--no-download", f"ytsearch5:{query}"])
    out = []
    for line in p.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[0].strip():
            try:
                dur = float(parts[2]) if parts[2] not in ("NA", "None", "") else 0
            except ValueError:
                dur = 0
            out.append((parts[0].strip(), parts[1].strip(), dur))
    return out

def pick(results):
    """Prefer 1-12 min videos (real news reports, not shorts/ads)."""
    cands = [r for r in results if 45 <= r[2] <= 720]
    if not cands:
        cands = [r for r in results if r[2] > 0]
    return cands[0] if cands else None

def download(vid, dest):
    p = run(["yt-dlp", "--no-check-certificate", "--extractor-args", "youtube:player_client=android",
             "-f", "bv*[height<=720]+ba/b[height<=720]/b",
             "--merge-output-format", "mp4",
             "-o", dest, f"https://www.youtube.com/watch?v={vid}"],
            timeout=300)
    return p.returncode == 0 and os.path.exists(dest)

def trim(src, start, dest):
    p = run(["ffmpeg", "-y", "-v", "error",
             "-ss", f"{start:.1f}", "-t", str(CLIP_LEN), "-i", src,
             "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
             "-c:v", "libx264", "-preset", "fast", "-crf", "23",
             "-an", dest], timeout=180)
    return p.returncode == 0

def main():
    work = os.path.abspath(sys.argv[1])
    segs = json.load(open(os.path.join(work, "segments.json")))
    got = 0
    for s in segs:
        sid = s["id"]
        out = os.path.join(work, f"clip_{sid}.mp4")
        if os.path.exists(out):
            print(f"  clip_{sid}: already exists, skip")
            got += 1
            continue
        query = s["headline"][:90] + " news report"
        print(f"  [{sid}] searching: {query[:60]}...")
        try:
            results = search(query)
        except Exception as e:
            print(f"  [{sid}] search failed: {e}")
            continue
        choice = pick(results)
        if not choice:
            print(f"  [{sid}] no usable video found")
            continue
        vid, title, dur = choice
        print(f"  [{sid}] -> {title[:55]} ({dur:.0f}s)")
        tmp = os.path.join(work, f"_dl_{sid}.mp4")
        try:
            if not download(vid, tmp):
                print(f"  [{sid}] download failed")
                continue
            start = max(0, dur / 2 - CLIP_LEN / 2) if dur else 10
            if trim(tmp, start, out):
                print(f"  clip_{sid}: OK")
                got += 1
            else:
                print(f"  [{sid}] trim failed")
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    print(f"clips ready: {got}/{len(segs)}")

if __name__ == "__main__":
    main()

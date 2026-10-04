#!/usr/bin/env python3
"""Download a YouTube thumbnail per story as the image fallback — no API key, no yt-dlp.

Strategy: scrape YouTube search results HTML for the story headline, take the
first video's thumbnail (i.ytimg.com). Plain HTTP fetches — works where yt-dlp
gets bot-blocked.

Usage: fetch_thumbs.py work_dir/
Reads work_dir/segments.json (needs "id" + "headline"), writes work_dir/thumb_<id>.jpg
Skips stories that already have a real video clip (clip_<id>.mp4).
compose.py priority: clip > thumb > og:image > gradient.
"""
import json, os, re, sys, urllib.request, urllib.parse

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}

def fetch(url, timeout=25, max_bytes=3_000_000):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(max_bytes)

def search_video_id(query):
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query + " news")
    try:
        html = fetch(url).decode("utf-8", "ignore")
    except Exception as e:
        print(f"    search fetch failed: {e}")
        return None
    for m in re.finditer(r'"videoId":"([A-Za-z0-9_-]{11})"', html):
        vid = m.group(1)
        ctx = html[max(0, m.start() - 200):m.start()]
        if "adSlot" in ctx or "promoted" in ctx.lower():
            continue
        return vid
    return None

def download_thumb(vid, dest):
    for quality in ("hqdefault", "mqdefault", "default"):
        try:
            data = fetch(f"https://i.ytimg.com/vi/{vid}/{quality}.jpg")
            if data[:3] == b"\xff\xd8\xff" and len(data) > 8000:
                with open(dest, "wb") as f:
                    f.write(data)
                return True
        except Exception:
            continue
    return False

def main():
    work = sys.argv[1]
    segs = json.load(open(os.path.join(work, "segments.json")))
    got = 0
    for s in segs:
        sid = s["id"]
        dest = os.path.join(work, f"thumb_{sid}.jpg")
        if os.path.exists(dest):
            got += 1
            continue
        if os.path.exists(os.path.join(work, f"clip_{sid}.mp4")):
            continue  # real clip wins, no thumb needed
        print(f"  [{sid}] thumb search: {s['headline'][:60]}...")
        vid = search_video_id(s["headline"][:90])
        if not vid:
            print("    no video found")
            continue
        if download_thumb(vid, dest):
            print(f"    thumb_{sid}: OK ({vid})")
            got += 1
        else:
            print("    thumb download failed")
    print(f"thumbs ready: {got}/{len(segs)}")

if __name__ == "__main__":
    main()

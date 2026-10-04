#!/usr/bin/env python3
"""Fetch one YouTube thumbnail per story as the image fallback.

Input:  work/segments.json  (needs "id" + "headline" per story)
Output: work/thumb_<id>.jpg

Video downloads are often blocked on datacenter IPs, but thumbnails
(i.ytimg.com) usually still load. compose.py prefers clip > thumb > img.
"""
import json, os, sys, subprocess, urllib.request

def run(cmd, timeout=120):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

def search_thumb(query):
    p = run(["yt-dlp", "--no-check-certificate", "--extractor-args",
             "youtube:player_client=android",
             "--print", "%(id)s\t%(thumbnail)s",
             "--no-download", f"ytsearch3:{query}"])
    for line in p.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 2 and parts[0].strip() and parts[1].strip().startswith("http"):
            return parts[0].strip(), parts[1].strip()
    return None, None

def candidates(tid, thumb):
    urls = []
    if thumb:
        urls.append(thumb)
    if tid:
        urls.append(f"https://i.ytimg.com/vi/{tid}/maxresdefault.jpg")
        urls.append(f"https://i.ytimg.com/vi/{tid}/hqdefault.jpg")
    return urls

def download(url, dest):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        if len(data) < 15000:  # missing maxres returns a tiny placeholder
            return False
        open(dest, "wb").write(data)
        return True
    except Exception:
        return False

def main():
    work = os.path.abspath(sys.argv[1])
    segs = json.load(open(os.path.join(work, "segments.json")))
    got = 0
    for s in segs:
        sid = s["id"]
        out = os.path.join(work, f"thumb_{sid}.jpg")
        if os.path.exists(out):
            print(f"  thumb_{sid}: already exists, skip")
            got += 1
            continue
        query = s["headline"][:90] + " news"
        print(f"  [{sid}] thumb search: {query[:55]}...")
        try:
            tid, thumb = search_thumb(query)
        except Exception as e:
            print(f"  [{sid}] search failed: {e}")
            continue
        if not tid:
            print(f"  [{sid}] no video found")
            continue
        ok = False
        for url in candidates(tid, thumb):
            if download(url, out):
                ok = True
                break
        print(f"  thumb_{sid}: {'OK' if ok else 'FAILED'}")
        got += ok
    print(f"thumbs ready: {got}/{len(segs)}")

if __name__ == "__main__":
    main()

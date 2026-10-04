#!/usr/bin/env python3
"""Download one representative image per story — no API key needed.

Strategy per story:
  1. Try the article's OpenGraph image (og:image) via the story link.
  2. Fallback: Google News RSS <media:content> / enclosure if present.
  3. Fallback: skip (compose.py uses the video clip or a gradient card).

Usage: fetch_images.py stories.json work_dir/
Writes work_dir/img_N.jpg (N = story id).
"""
import json, os, re, sys, html
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def fetch(url, timeout=20, max_bytes=8_000_000):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        ctype = r.headers.get("Content-Type", "")
        data = r.read(max_bytes)
    return data, ctype

def og_image(article_url):
    try:
        data, ctype = fetch(article_url)
        if "html" not in ctype:
            return None
        page = data.decode("utf-8", "ignore")
        m = re.search(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
            page, re.I)
        if not m:
            m = re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                page, re.I)
        if m:
            return html.unescape(m.group(1))
    except Exception as e:
        print(f"    og scrape failed: {e}")
    return None

def is_image(data):
    return (data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n"
            or data[:4] == b"GIF8" or data[8:12] == b"WEBP")

def save_image(url, dest):
    try:
        data, ctype = fetch(url)
        if not is_image(data) and "image" not in ctype:
            return False
        with open(dest, "wb") as f:
            f.write(data)
        print(f"    saved {len(data)//1024}KB")
        return True
    except Exception as e:
        print(f"    download failed: {e}")
        return False

def main():
    stories = json.load(open(sys.argv[1]))
    work = sys.argv[2]
    os.makedirs(work, exist_ok=True)
    got = 0
    for s in stories:
        sid = s["id"]
        dest = os.path.join(work, f"img_{sid}.jpg")
        if os.path.exists(dest):
            got += 1
            continue
        print(f"  [{sid}] {s['title'][:55]}")
        img = None
        if s.get("link"):
            print("    trying og:image...")
            img = og_image(s["link"])
        if not img and s.get("image"):
            img = s["image"]
        if img and img.startswith("http"):
            print(f"    {img[:70]}")
            if save_image(img, dest):
                got += 1
            continue
        print("    no image found, skipping")
    print(f"images ready: {got}/{len(stories)}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fetch top trending international + crime news from Google News RSS.

Outputs stories.json: list of {id, title, source, description, link, pubDate, image_query}
Free, no API key needed.
"""
import json, re, sys, html, difflib, urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

UA = {'User-Agent': 'Mozilla/5.0'}

FEEDS = {
    "top":      "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    "world":    "https://news.google.com/rss/search?q=world%20news&hl=en-US&gl=US&ceid=US:en",
    "crime":    "https://news.google.com/rss/search?q=crime&hl=en-US&gl=US&ceid=US:en",
    "trending": "https://news.google.com/rss/search?q=breaking%20news&hl=en-US&gl=US&ceid=US:en",
}

CRIME_WORDS = re.compile(
    r"\b(kill|killed|killing|murder|shot|shooting|stabbed|stabbing|rape|raped|"
    r"assault|attack|attacked|arrest|arrested|prison|jail|trial|court|"
    r"sentenced|execution|executed|crime|criminal|police|suspect|victim|"
    r"bomb|terror|hostage|kidnap|fraud|scam|robbery|theft|gang|drug|"
    r"smuggling|abuse|deadly|crash|missile|airstrike|war|explosion|axe)\b", re.I)

# sports / entertainment / gossip - not news-reel material
EXCLUDE = re.compile(
    r"\b(box office|movie|film|series|season|episode|game|match|win|loss|"
    r"touchdown|goal|coach|playoff|tournament|album|concert|tour|song|"
    r"singer|actor|actress|celebrity|fashion|recipe|horoscope|lottery)\b", re.I)

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def clean_title(raw):
    # Google News titles look like "Headline - Source Name"
    parts = raw.rsplit(" - ", 1)
    if len(parts) == 2 and len(parts[1]) < 60:
        return parts[0].strip(), parts[1].strip()
    return raw.strip(), ""

def norm(t):
    return re.sub(r"[^a-z0-9 ]", "", t.lower())

def main():
    want = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    seen, stories = set(), []
    for name, url in FEEDS.items():
        try:
            root = ET.fromstring(fetch(url))
        except Exception as e:
            print(f"[warn] feed {name} failed: {e}", file=sys.stderr)
            continue
        for it in root.find("channel").findall("item"):
            raw = html.unescape(it.findtext("title") or "")
            title, source = clean_title(raw)
            n = norm(title)
            if not n or any(difflib.SequenceMatcher(None, n, s).ratio() > 0.72 for s in seen):
                continue
            seen.add(n)
            desc = html.unescape(re.sub(r"<[^>]+>", "", it.findtext("description") or ""))[:300]
            if EXCLUDE.search(title + " " + desc):
                continue
            try:
                pub = parsedate_to_datetime(it.findtext("pubDate")).astimezone(timezone.utc)
            except Exception:
                pub = datetime.now(timezone.utc)
            age_h = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
            crime = bool(CRIME_WORDS.search(title + " " + desc))
            # score: fresher is better, crime gets a boost
            score = max(0, 48 - age_h) + (30 if crime else 0) + (10 if name in ("top", "world") else 0)
            stories.append({
                "title": title, "source": source, "description": desc,
                "link": it.findtext("link") or "", "pubDate": pub.isoformat(),
                "age_hours": round(age_h, 1), "crime": crime,
                "image_query": title, "score": score, "feed": name,
            })
    stories.sort(key=lambda s: -s["score"])
    # diversity: avoid same source back-to-back when possible
    picked, used_sources = [], {}
    for s in stories:
        if len(picked) >= want:
            break
        if used_sources.get(s["source"], 0) >= 2:
            continue
        picked.append(s); used_sources[s["source"]] = used_sources.get(s["source"], 0) + 1
    for i, s in enumerate(picked, 1):
        s["id"] = i
        s.pop("score", None); s.pop("feed", None)
    out = sys.argv[2] if len(sys.argv) > 2 else "stories.json"
    json.dump(picked, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"picked {len(picked)} stories -> {out}")
    for s in picked:
        tag = "CRIME " if s["crime"] else "      "
        print(f"  {tag}{s['age_hours']:>5}h  {s['title'][:80]} ({s['source']})")

if __name__ == "__main__":
    main()

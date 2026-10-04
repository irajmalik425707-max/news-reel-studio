#!/usr/bin/env python3
"""Pick stories by number for the reel (the 'choose' step of News Reel Studio).

Usage: python3 choose.py stories.json chosen.json 1 3 4
   or: python3 choose.py stories.json chosen.json auto   (top 5, for auto mode)

Reads stories.json (from fetch_news.py), keeps the chosen indices (1-based,
in the order shown), renumbers ids 1..N, writes chosen.json.
"""
import json, sys

def main():
    src, out = sys.argv[1], sys.argv[2]
    picks = sys.argv[3:]
    stories = json.load(open(src))
    if picks == ["auto"]:
        chosen = stories[:5]
    else:
        idx = []
        for p in picks:
            for part in p.replace(",", " ").split():
                i = int(part)
                if 1 <= i <= len(stories) and i not in idx:
                    idx.append(i)
        chosen = [stories[i - 1] for i in idx]
    for n, s in enumerate(chosen, 1):
        s["id"] = n
    json.dump(chosen, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"chosen {len(chosen)} stories -> {out}")
    for s in chosen:
        print(f"  {s['id']}. {s['title'][:75]} ({s['source']})")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Write segments.json from chosen stories — template-based, no LLM or API key.

Input:  chosen.json (from choose.py: [{id, title, source, description, crime}])
Output: segments.json [{id, kicker, headline, source, text}]

text = spoken-form voiceover, ~40-60 words: hook + description condensed + closer.
"""
import json, os, re, sys

CLOSERS = [
    "We'll keep following this story as it develops.",
    "More updates as this story unfolds.",
    "Stay tuned — this story is still developing.",
    "We'll bring you more as details emerge.",
]

def clean_sentence(s):
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(?i)^(breaking|live updates|watch|read more)[:\-–]\s*", "", s)
    return s

def split_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text or "")
    out = []
    for p in parts:
        s = clean_sentence(p)
        if len(s) <= 25:
            continue
        if ".com" in s or "http" in s:      # related-link junk
            continue
        if len(s) > 220:                     # concatenated titles
            continue
        if not re.search(r"[a-z]", s):        # ALL-CAPS title fragments
            continue
        out.append(s)
    return out

def related_headlines(story):
    """Google News RSS descriptions look like:
    '{Title}  {Source}{Related 1}  {src2.com}{Related 2}  ...'
    The related headlines (with glued source names stripped) make a good body.
    """
    desc = (story.get("description", "") or "").replace("\xa0", " ")
    parts = [p.strip() for p in re.split(r"\s{2,}", desc) if p.strip()]
    main_source = (story.get("source", "") or "").strip()
    sents = []
    for p in parts[1:]:  # skip the title itself (parts[0])
        raw = p
        p = re.sub(r"^[\w-]+\.(com|org|net|io)\s*", "", p)  # glued domain
        # strip glued source names (loop: "NBC NewsJapan" -> "NBC" then "News")
        for _ in range(3):
            p2 = re.sub(r"^(?:CNN|BBC|AP|NPR|NBC|CBS|ABC|Fox News|Sky News|Yahoo|"
                        r"Reuters|Al Jazeera|NHK|DW|PBS|CNBC|US News|UK News|"
                        r"World News|News)\s*", "", p)
            if p2 == p:
                break
            p = p2
        if main_source:
            p = re.sub(r"^" + re.escape(main_source) + r"\s*", "", p)
        p = clean_sentence(p)
        if len(p) <= 25 or len(p) > 220:
            continue
        if ".com" in p or "http" in p or not re.search(r"[a-z]", p):
            continue
        if re.search(r"[.!?]$", raw.strip()):
            pass  # complete sentence
        elif len(raw.strip().split()[-1]) <= 3:
            continue  # truncated mid-word ("...brutal and", "...attack on Sau")
        else:
            p += "."
        if p not in sents:
            sents.append(p)
    return sents

def condense(story, max_words=48):
    sents = related_headlines(story)
    out, count = [], 0
    for s in sents:
        w = len(s.split())
        if count + w > max_words and out:
            break
        out.append(s)
        count += w
        if len(out) >= 3:
            break
    text = " ".join(out)
    if not text:
        # fallback: title + generic line
        text = headline_of(story.get("title", "")) + ". Details are still emerging."
    return text

def headline_of(title):
    t = re.sub(r"\s+", " ", title).strip()
    # strip trailing source suffixes like " - CNN"
    t = re.sub(r"\s+[-–|]\s+[^-–|]{2,30}$", "", t)
    return t[:90]

def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "segments.json"
    stories = json.load(open(src))
    segs = []
    for i, s in enumerate(stories):
        crime = bool(s.get("crime"))
        if crime:
            kicker, hook = "CRIME ALERT", "Crime alert."
        elif "trending" in (s.get("feed", "") or ""):
            kicker, hook = "TRENDING", "Trending now."
        else:
            kicker, hook = "WORLD NEWS", "In world news."
        body = condense(s, 48)
        closer = CLOSERS[i % len(CLOSERS)]
        text = f"{hook} {body} {closer}"
        segs.append({
            "id": s.get("id", i + 1),
            "kicker": kicker,
            "headline": headline_of(s.get("title", "")),
            "source": s.get("source", ""),
            "text": text,
        })
    json.dump(segs, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"wrote {len(segs)} segments -> {out}")
    for s in segs:
        print(f"  {s['id']}. [{s['kicker']}] {len(s['text'].split())} words")

if __name__ == "__main__":
    main()

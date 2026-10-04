#!/usr/bin/env python3
"""Generate a cinematic AI news visual per story (free, no API key).

Uses pollinations.ai image API. Each story gets a dramatic, photorealistic
vertical visual matching its content — animated later with Ken Burns in
compose.py for an engaging look.

Usage: fetch_ai.py work_dir/
Reads work_dir/segments.json (needs "id" + "headline"), writes work_dir/ai_<id>.jpg
Skips stories that already have a real video clip (clip_<id>.mp4).
compose.py priority: clip > ai image > thumbnail > og:image > gradient.
"""
import json, os, re, sys, urllib.request, urllib.parse

def visual_prompt(headline):
    h = (headline or "").lower()
    place_m = re.search(r"(?i)\b(?:in|on|at|of|near)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})", headline or "")
    place = place_m.group(1) if place_m else "the city"
    base = "cinematic breaking news footage still, photorealistic, dramatic lighting, vertical 9:16 composition"
    if any(w in h for w in ("stab", "knife")):
        scene = f"police cars with flashing red and blue lights at a stabbing crime scene on a residential street in {place} at dusk, yellow crime scene tape, officers investigating"
    elif any(w in h for w in ("shoot", "gunfire", "gunman")):
        scene = f"police tactical units and flashing patrol cars at a shooting crime scene in {place} at night, crime scene tape, dramatic emergency lights"
    elif any(w in h for w in ("murder", "homicide", "killed", "dead")):
        scene = f"homicide investigation at night in {place}, police cars with flashing lights, forensic officers, crime scene tape, moody dramatic lighting"
    elif any(w in h for w in ("arrest", "suspect", "charged")):
        scene = f"police officers escorting a handcuffed suspect to a patrol car in {place}, flashing police lights at night, dramatic news footage style"
    elif any(w in h for w in ("fire", "explosion", "blast")):
        scene = f"massive fire with thick black smoke and firefighters battling flames in {place} at night, dramatic orange glow, news footage style"
    elif any(w in h for w in ("missile", "strike", "attack", "war")):
        scene = f"dramatic night sky with missile trails and explosions over a city skyline, breaking news footage style, cinematic"
    elif any(w in h for w in ("protest", "riot", "raid")):
        scene = f"police in riot gear facing protesters on a city street at night, dramatic lighting, breaking news footage style"
    elif any(w in h for w in ("court", "trial", "jailed", "prison", "sentence")):
        scene = f"courthouse exterior with police presence, dramatic cloudy sky, gavel symbolism, cinematic news style"
    elif any(w in h for w in ("cyber", "hack", "scam", "fraud")):
        scene = f"dark room with glowing computer screens showing code, hooded figure silhouette, dramatic blue lighting, cybercrime news style"
    else:
        scene = f"breaking news scene in {place}, police lights and dramatic atmosphere at night, cinematic"
    return f"{scene}, {base}"

def fetch_image(prompt, dest, timeout=150):
    q = urllib.parse.quote(prompt[:480])
    url = (f"https://image.pollinations.ai/prompt/{q}"
           f"?width=768&height=1344&nologo=true&seed=7&model=flux")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        if data[:3] == b"\xff\xd8\xff" and len(data) > 20000:
            with open(dest, "wb") as f:
                f.write(data)
            return True
        print(f"    bad image data ({len(data)} bytes)")
    except Exception as e:
        print(f"    ai fetch failed: {e}")
    return False

def main():
    work = sys.argv[1]
    segs = json.load(open(os.path.join(work, "segments.json")))
    got = 0
    for s in segs:
        sid = s["id"]
        dest = os.path.join(work, f"ai_{sid}.jpg")
        if os.path.exists(dest):
            got += 1
            continue
        if os.path.exists(os.path.join(work, f"clip_{sid}.mp4")):
            continue  # real clip wins
        print(f"  [{sid}] ai visual: {s['headline'][:55]}...")
        prompt = visual_prompt(s["headline"])
        if fetch_image(prompt, dest):
            print(f"    ai_{sid}: OK")
            got += 1
        else:
            print(f"    ai_{sid}: FAILED")
    print(f"ai visuals ready: {got}/{len(segs)}")

if __name__ == "__main__":
    main()

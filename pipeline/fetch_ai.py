#!/usr/bin/env python3
"""Generate 3 cinematic AI news visuals per story (free, no API key).

Uses pollinations.ai image API. Three different shots per story so the reel
cuts between visuals instead of sitting on one image:
  1. wide establishing shot
  2. dramatic close-up / detail
  3. aftermath / different angle

Usage: fetch_ai.py work_dir/
Reads work_dir/segments.json (needs "id" + "headline"), writes work_dir/ai_<id>_<1..3>.jpg
Skips stories that already have a real video clip (clip_<id>.mp4).
compose.py priority: clip > ai visuals > thumbnail > og:image > gradient.
"""
import json, os, re, sys, urllib.request, urllib.parse

def place_of(headline):
    m = re.search(r"\b(?:in|on|at|of|near)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})", headline or "")
    return m.group(1) if m else "the city"

def crime_scene(h):
    h = h.lower()
    if any(w in h for w in ("stab", "knife")):
        return "stabbing crime scene"
    if any(w in h for w in ("shoot", "gunfire", "gunman")):
        return "shooting crime scene"
    if any(w in h for w in ("murder", "homicide", "killed", "dead", "body")):
        return "homicide investigation scene"
    if any(w in h for w in ("arrest", "suspect", "charged")):
        return "police arrest scene"
    if any(w in h for w in ("fire", "explosion", "blast")):
        return "massive fire with firefighters"
    if any(w in h for w in ("missile", "strike", "attack", "war")):
        return "missile strike on city at night"
    if any(w in h for w in ("protest", "riot", "raid")):
        return "police raid on city street at night"
    if any(w in h for w in ("court", "trial", "jailed", "prison", "sentence")):
        return "courthouse with police presence"
    if any(w in h for w in ("cyber", "hack", "scam", "fraud")):
        return "cybercrime investigation, glowing screens"
    return "breaking news crime scene"

def shot_prompts(headline):
    place = place_of(headline)
    scene = crime_scene(headline)
    base = "cinematic breaking news footage still, photorealistic, dramatic lighting, vertical 9:16 composition, no text, no watermark"
    return [
        f"wide establishing shot of {scene} on a residential street in {place} at dusk, police cars with flashing red and blue lights, yellow crime scene tape, {base}",
        f"dramatic close-up at {scene} in {place}, flashing police lights reflecting, crime scene tape in foreground, shallow depth of field, {base}",
        f"{scene} in {place} from a different angle, officers investigating, emergency vehicles, night, moody cinematic atmosphere, {base}",
    ]

def fetch_image(prompt, dest, timeout=150):
    q = urllib.parse.quote(prompt[:480])
    import random
    seed = random.randint(1, 999999)
    url = (f"https://image.pollinations.ai/prompt/{q}"
           f"?width=768&height=1344&nologo=true&seed={seed}&model=flux")
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
    got, total = 0, 0
    for s in segs:
        sid = s["id"]
        if os.path.exists(os.path.join(work, f"clip_{sid}.mp4")):
            continue  # real clip wins
        prompts = shot_prompts(s["headline"])
        for j, prompt in enumerate(prompts, 1):
            dest = os.path.join(work, f"ai_{sid}_{j}.jpg")
            total += 1
            if os.path.exists(dest):
                got += 1
                continue
            print(f"  [{sid}] ai shot {j}/3: {s['headline'][:45]}...")
            if fetch_image(prompt, dest):
                print(f"    ai_{sid}_{j}: OK")
                got += 1
            else:
                print(f"    ai_{sid}_{j}: FAILED")
    print(f"ai visuals ready: {got}/{total}")

if __name__ == "__main__":
    main()

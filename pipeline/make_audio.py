#!/usr/bin/env python3
"""Synthesize one MP3 per segment with free edge-tts (no API key).

Usage: python3 make_audio.py segments.json work/
Writes work/seg_N.mp3 and work/timings.json [{id, duration}].
Voice default: en-US-GuyNeural (deep male, newsreader style).
Override with REEL_VOICE env var.
"""
import asyncio
import json, os, sys, subprocess

VOICE = os.environ.get("REEL_VOICE", "en-US-RogerNeural")
FALLBACK_VOICE = "en-US-ChristopherNeural"

def duration(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(p.stdout.strip())

def to_ssml(text):
    """Wrap the script in SSML with natural pauses so delivery doesn't sound flat."""
    import re, html as htmllib
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    inner = '<break time="450ms"/>'.join(htmllib.escape(p) for p in parts if p)
    return (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            f'xml:lang="en-US"><voice name="{VOICE}">'
            f'<prosody rate="-4%" pitch="+2%">{inner}</prosody>'
            f"</voice></speak>")

async def synth_edge(text, out):
    import edge_tts
    ssml = to_ssml(text)
    try:
        await edge_tts.Communicate(ssml, VOICE).save(out)
    except Exception:
        # fallback voice if the primary isn't available
        ssml2 = ssml.replace(VOICE, FALLBACK_VOICE)
        await edge_tts.Communicate(ssml2, FALLBACK_VOICE).save(out)

def synth_gtts(text, out):
    from gtts import gTTS
    gTTS(text=text, lang="en").save(out)

async def synth(text, out):
    try:
        await synth_edge(text, out)
    except Exception as e:
        print(f"    edge-tts failed ({e}); falling back to gTTS", flush=True)
        synth_gtts(text, out)

async def main_async(segs, work):
    timings = []
    for s in segs:
        out = os.path.join(work, f"seg_{s['id']}.mp3")
        if not os.path.exists(out):
            await synth(s["text"], out)
        d = duration(out)
        timings.append({"id": s["id"], "duration": d})
        print(f"  seg_{s['id']}: {d:.1f}s")
    json.dump(timings, open(os.path.join(work, "timings.json"), "w"), indent=1)

def main():
    segs = json.load(open(sys.argv[1]))
    work = sys.argv[2]
    os.makedirs(work, exist_ok=True)
    asyncio.run(main_async(segs, work))
    print("audio done")

if __name__ == "__main__":
    main()

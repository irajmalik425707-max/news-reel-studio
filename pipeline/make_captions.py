#!/usr/bin/env python3
"""Word-timed captions for the news reel, in the @themediaanswer CapCut style.

Input:  work/segments.json [{id, text}], work/seg_<id>.mp3
Output: work/cap_<id>.ass  (one ASS subtitle file per segment)

Two styles (--style):
  white  - extra-bold white text, thick black outline  (like "one simple")
  black  - extra-bold black text, thick white outline  (like "make"/"to batch")

Words are grouped into short CapCut-style phrase pops using whisper
word timestamps (faster-whisper tiny.en, local, free).
"""
import json, os, sys, subprocess
import numpy as np

def caption_font():
    # Anton (bundled in pipeline/fonts, installed by workflow) for reel-style look
    return "Anton"

FONT = caption_font()
FSIZE = 92

def transcribe_words(mp3):
    from faster_whisper import WhisperModel
    if not hasattr(transcribe_words, "m"):
        transcribe_words.m = WhisperModel("tiny.en", device="cpu",
                                          compute_type="int8")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", mp3,
                    "-ar", "16000", "-ac", "1",
                    "-f", "f32le", "-acodec", "pcm_f32le",
                    "/tmp/_cap.raw"], check=True)
    audio = np.fromfile("/tmp/_cap.raw", dtype=np.float32)
    segs, _ = transcribe_words.m.transcribe(audio, word_timestamps=True)
    return [w for s in segs for w in s.words if w.word.strip()]

def chunks(words, max_chars=26, max_words=4):
    cur, out = [], []
    for w in words:
        cur.append(w)
        text = "".join(x.word for x in cur)
        if len(cur) >= max_words or len(text) >= max_chars:
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out

def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def ass_esc(t):
    return t.replace("{", "").replace("}", "")

def write_ass(path, chunks, style):
    if style == "black":
        primary, outline = "&H00111111", "&H00FFFFFF"  # near-black text, white edge
    else:
        primary, outline = "&H00FFFFFF", "&H00000000"  # white text, black edge
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{FONT},{FSIZE},{primary},{primary},{outline},&H80000000,-1,0,0,0,100,100,0.5,0,1,8,2,2,60,60,420,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    evs = []
    for ch in chunks:
        start = max(0.0, ch[0].start - 0.03)
        end = ch[-1].end + 0.08
        text = ass_esc("".join(w.word for w in ch)).strip()
        evs.append(f"Dialogue: 0,{ts(start)},{ts(end)},Cap,,0,0,0,,{text}")
    open(path, "w").write(head + "\n".join(evs) + "\n")

def main():
    work = os.path.abspath(sys.argv[1])
    style = sys.argv[2] if len(sys.argv) > 2 else "white"
    assert style in ("white", "black"), "style must be white|black"
    segs = json.load(open(os.path.join(work, "segments.json")))
    n = 0
    for s in segs:
        mp3 = os.path.join(work, f"seg_{s['id']}.mp3")
        if not os.path.exists(mp3):
            print(f"  cap_{s['id']}: no audio, skip")
            continue
        words = transcribe_words(mp3)
        if not words:
            print(f"  cap_{s['id']}: no words, skip")
            continue
        out = os.path.join(work, f"cap_{s['id']}.ass")
        write_ass(out, chunks(words), style)
        n += 1
        print(f"  cap_{s['id']}: {len(words)} words -> {style}")
    print(f"captions ready: {n}/{len(segs)} (style={style})")

if __name__ == "__main__":
    main()

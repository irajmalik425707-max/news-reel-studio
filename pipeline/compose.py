#!/usr/bin/env python3
"""Compose the final 9:16 news reel with ffmpeg.

Inputs (work/): img_N.jpg, seg_N.mp3, timings.json, segments.json
Output: reel-YYYYMMDD.mp4 (1080x1920, 30fps, H.264 + AAC)

Style: Ken Burns pan/zoom per story, top kicker badge (CRIME/WORLD/TRENDING),
bottom headline card, thin progress bar, hard cuts between stories.
"""
import json, os, sys, subprocess, textwrap, datetime

W, H, FPS = 1080, 1920, 30
GAP = 0.45          # silence between stories
TAIL = 0.55         # extra hold at end of each story
def pick_font(*paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[-1]  # last resort; ffmpeg will error clearly if missing

FONT_B = pick_font("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
FONT_R = pick_font("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONT_BLK = pick_font("/usr/share/fonts/truetype/noto/NotoSans-Black.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

def sh(cmd, **kw):
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if p.returncode != 0:
        print("CMD:", " ".join(cmd), file=sys.stderr)
        print(p.stderr[-2000:], file=sys.stderr)
        sys.exit(1)
    return p

def esc(t):
    return t.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:")

def wrap(headline, width=24, max_lines=3):
    lines = textwrap.wrap(headline, width=width)
    return lines[:max_lines]

def main():
    work = os.path.abspath(sys.argv[1])
    segs = json.load(open(os.path.join(work, "segments.json")))
    timings = {t["id"]: t["duration"] for t in json.load(open(os.path.join(work, "timings.json")))}
    out = sys.argv[2] if len(sys.argv) > 2 else \
        os.path.join(work, f"reel-{datetime.date.today():%Y%m%d}.mp4")

    # ---- per-story durations ----
    durs = []
    for s in segs:
        durs.append(timings[s["id"]] + GAP + TAIL)
    total = sum(durs)

    seg_files, audio_inputs = [], []
    t0 = 0.0
    for idx, s in enumerate(segs):
        dur = durs[idx]
        frames = int(dur * FPS)
        img = os.path.join(work, f"img_{s['id']}.jpg")
        thumb = os.path.join(work, f"thumb_{s['id']}.jpg")
        clip = os.path.join(work, f"clip_{s['id']}.mp4")
        vfile = os.path.join(work, f"vseg_{s['id']}.mp4")

        # Visual priority: real video clip > YouTube thumbnail > og:image > gradient
        if os.path.exists(clip):
            inp = ["-stream_loop", "-1", "-i", clip]
            vf = (f"scale=1080:1920:force_original_aspect_ratio=increase,"
                  f"crop=1080:1920,setsar=1,format=yuv420p")
            print(f"  vseg_{s['id']}: using VIDEO clip")
        else:
            # Ken Burns: alternate slow zoom-in / zoom-out
            if idx % 2 == 0:
                zb = f"z='min(zoom+0.0011,1.28)'"
            else:
                zb = f"z='if(eq(on,1),1.28,max(zoom-0.0011,1.0))'"
            vf = (
                f"scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
                f"zoompan={zb}:d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
                f"format=yuv420p"
            )
            use_img = thumb if os.path.exists(thumb) else img
            if os.path.exists(use_img):
                inp = ["-loop", "1", "-i", use_img]
                print(f"  vseg_{s['id']}: using image {os.path.basename(use_img)}")
            else:  # fallback: dark gradient card if image missing
                inp = ["-f", "lavfi", "-i",
                       f"color=c=0x141821:s={W}x{H}:r={FPS}:d={dur}"]
                vf = f"format=yuv420p"

        # ---- overlays ----
        lines = wrap(s["headline"])
        n = len(lines)
        fsize = 60
        card_h = 40 + n * 78 + 40
        card_y = H - card_h - 90
        kicker = s.get("kicker", "TOP NEWS").upper()
        kcol = "0xC81E1E" if "CRIME" in kicker else "0x1E5AC8"

        filters = [vf]
        # readability gradients
        filters.append(f"drawbox=x=0:y=0:w={W}:h=300:c=black@0.55:t=fill")
        filters.append(f"drawbox=x=0:y={H-760}:w={W}:h=760:c=black@0.55:t=fill")
        # kicker badge
        filters.append(f"drawbox=x=60:y=90:w=340:h=84:c={kcol}:t=fill")
        filters.append(
            f"drawtext=fontfile={FONT_BLK}:text='{esc(kicker)}':fontsize=44:"
            f"fontcolor=white:x=80:y=108")
        # story counter
        filters.append(
            f"drawtext=fontfile={FONT_R}:text='{idx+1} / {len(segs)}':fontsize=40:"
            f"fontcolor=white:x={W-180}:y=108")
        # headline card
        filters.append(f"drawbox=x=40:y={card_y}:w={W-80}:h={card_h}:c=black@0.62:t=fill")
        y = card_y + 44
        for ln in lines:
            filters.append(
                f"drawtext=fontfile={FONT_B}:text='{esc(ln)}':fontsize={fsize}:"
                f"fontcolor=white:x=80:y={y}")
            y += 78
        # source line (just below headline card)
        filters.append(
            f"drawtext=fontfile={FONT_R}:text='{esc('Source: ' + s.get('source',''))}':"
            f"fontsize=32:fontcolor=white@0.8:x=80:y={H-72}")
        # progress bar (overall reel progress)
        bar_w = 14
        filters.append(
            f"drawbox=x=0:y={H-bar_w}:w={W}:h={bar_w}:c=white@0.25:t=fill")
        p0, p1 = t0 / total, (t0 + dur) / total
        filters.append(
            f"drawbox=x=0:y={H-bar_w}:w='{W}*({p0}+({p1}-{p0})*t/{dur:.3f})':h={bar_w}:c=0xE11D2E:t=fill")
        # word-timed captions (CapCut style) burned mid-screen
        cap = os.path.join(work, f"cap_{s['id']}.ass")
        if os.path.exists(cap):
            filters.append(f"subtitles=filename='{cap}'")
        # fade in/out on first/last segment
        if idx == 0:
            filters.append("fade=t=in:st=0:d=0.4")
        if idx == len(segs) - 1:
            filters.append(f"fade=t=out:st={dur-0.6:.2f}:d=0.6")

        sh(["ffmpeg", "-y", *inp, "-t", f"{dur:.2f}",
            "-vf", ",".join(filters),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-r", str(FPS), "-pix_fmt", "yuv420p", vfile])
        seg_files.append(vfile)
        audio_inputs += [os.path.join(work, f"seg_{s['id']}.mp3")]
        t0 += dur
        print(f"  vseg_{s['id']}: {dur:.1f}s video OK")

    # ---- concat video ----
    lst = os.path.join(work, "vlist.txt")
    with open(lst, "w") as f:
        for v in seg_files:
            f.write(f"file '{v}'\n")
    vcat = os.path.join(work, "vcat.mp4")
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
        "-c", "copy", vcat])

    # ---- audio: pad each segment to its video duration, then concat ----
    af = []
    for i, a in enumerate(audio_inputs):
        af += ["-i", a]
    pads = "".join(
        f"[{i}:a]aresample=44100,apad=whole_dur={durs[i]:.2f}[pa{i}];"
        for i in range(len(audio_inputs)))
    pads += "".join(f"[pa{i}]" for i in range(len(audio_inputs)))
    pads += f"concat=n={len(audio_inputs)}:v=0:a=1[aout]"
    acat = os.path.join(work, "acat.m4a")
    sh(["ffmpeg", "-y", *af, "-filter_complex", pads,
        "-map", "[aout]", "-c:a", "aac", "-b:a", "128k", acat])

    # ---- mux ----
    sh(["ffmpeg", "-y", "-i", vcat, "-i", acat,
        "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart",
        "-shortest", out])
    print(f"DONE -> {out}  ({os.path.getsize(out)//1024} KB)")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "csv=p=0", out],
                           capture_output=True, text=True)
    print(f"final duration: {float(probe.stdout.strip()):.1f}s")

if __name__ == "__main__":
    main()

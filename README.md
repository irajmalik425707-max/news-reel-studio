# News Reel Studio — free, on GitHub

A SaaS-style tool that turns trending news into 9:16 reels. 100% free using
GitHub Pages (website) + GitHub Actions (backend). No servers, no API keys.

## How it works

- **Website** (`web/`, GitHub Pages): trending news list, tap stories to
  select, "Build Reel" button, reel history with watch/download.
- **Auto reels**: `build-reel.yml` runs on schedule (twice daily) and builds
  a reel from the top 5 trending stories — no setup needed, videos just
  appear under "Your reels".
- **Manual builds** (optional): select stories on the site and press
  "Build Reel" — needs the one-time Setup (GitHub username + token +
  build key) on the site.
- **Trending refresh** (`.github/workflows/trending.yml`): every 6 hours
  fetches Google News RSS and updates `web/stories.json`.
- **Reel build** (`.github/workflows/build-reel.yml`): triggered from the
  website. Fetches clips (YouTube), images, free TTS voiceover (edge-tts),
  word-timed captions (whisper), composes 1080×1920 MP4 with ffmpeg, and
  publishes it as a GitHub Release. ~10–15 min per reel.
- **Team access**: anyone with the link + build key can trigger builds.
  The build key is checked inside the workflow, so random visitors can't
  burn your free Actions minutes.

## Setup (one time, ~10 min)

1. Create a **public** GitHub repo named `news-reel-studio`, push this code.
2. Repo → Settings → Secrets and variables → Actions → New repository secret:
   - Name: `BUILD_KEY`, Value: any secret phrase (share with your team).
   - ⚠️ This secret is REQUIRED — builds refuse to run without it.
3. Repo → Settings → Pages → Build and deployment:
   - Source: **Deploy from a branch** → Branch: `main`, Folder: `/web` → Save.
4. Create a token: `github.com/settings/tokens/new` → note `news-reel`,
   tick **`repo`** scope → Generate. (Keep it private — it goes in your
   browser only, never in the code.)
5. Open your Pages URL (`https://<username>.github.io/news-reel-studio/`),
   enter GitHub username + token + build key in Setup → Save.
6. Done. Tap stories → Build reel → video appears under "Your reels".

## Free-tier math

GitHub Actions free: 2,000 min/month. One reel ≈ 10–15 min → **130+ reels/month free**.
Releases storage: plenty for short reels.

## Pipeline scripts

`pipeline/`: `fetch_news.py` (Google News RSS) → `choose.py` →
`write_script.py` (template voiceover, no LLM) → `fetch_images.py` (og:image) →
`fetch_clips.py` (yt-dlp, 12s YouTube clips) → `make_audio.py` (edge-tts) →
`make_captions.py` (faster-whisper word timings, CapCut style) →
`compose.py` (ffmpeg 1080×1920).

Run locally the same way the workflow does — see `build-reel.yml`.

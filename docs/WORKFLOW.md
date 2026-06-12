# YouTube Automation — System Workflow

## Overview

Fully automated pipeline: picks a topic → writes a script → generates voice + video → uploads to YouTube. Runs daily via Windows Task Scheduler with zero manual input.

---

## Full Pipeline Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ENTRY POINTS                                         │
│                                                                             │
│  [Windows Task Scheduler] ──daily──► auto_daily.py   (fully automatic)     │
│  [Manual]                           python main.py "topic"  (test/manual)  │
│  [Manual upload only]               python upload_now.py    (upload only)  │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │      auto_daily.py         │
                    │                           │
                    │  1. Load topic_history    │
                    │  2. Pick unused topic     │
                    │     ├─ from SEED_TOPICS   │
                    │     └─ or ask Ollama AI   │
                    └─────────────┬─────────────┘
                                  │ topic string
                    ┌─────────────▼─────────────┐
                    │      main.py               │
                    │    run_pipeline(topic)     │
                    └─────────────┬─────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼  STEP 1                 ▼  STEP 2                 ▼  STEP 3
┌───────────────┐      ┌──────────────────┐      ┌──────────────────────┐
│ script_gen.py │      │   tts_gen.py     │      │  thumbnail_gen.py    │
│               │      │                  │      │                      │
│ Ollama LLM    │      │ edge_tts (Azure  │      │ Pollinations AI      │
│ writes 4-part │─────►│ Neural TTS)      │      │ generates background │
│ narration     │      │                  │      │ image via prompt     │
│ script        │      │ Split into 400-  │      │      ↓ fail?         │
│ (~2,400 words │      │ word chunks,     │      │ Pexels photo         │
│  = ~14-16 min)│      │ synthesize each  │      │ fallback             │
│               │      │ chunk to MP3,    │      │      ↓               │
│ + metadata:   │      │ concat with      │      │ Draw title overlay   │
│   title       │      │ ffmpeg           │      │ (yellow bold text    │
│   description │      │      ↓           │      │  + red accent bar)   │
│   tags        │      │ Generate SRT     │      │      ↓               │
│   keywords    │      │ subtitle file    │      │ Save as JPG          │
└───────┬───────┘      └────────┬─────────┘      └──────────┬───────────┘
        │                       │                            │
        │                       ▼                            │
        │         ┌─────────────────────────┐                │
        │         │  Output (temp/)         │                │
        │         │  audio.mp3              │                │
        │         │  audio.srt              │                │
        └─────────┴─────────────┬───────────┘                │
                                │                            │
                    ┌───────────▼────────────────────────────┤
                    │           STEP 4                       │
                    │        video_gen.py                    │
                    │                                        │
                    │  Collect background footage            │
                    │  to match audio duration:             │
                    │                                        │
                    │  Phase 1: Pexels Videos   ────────┐   │
                    │  Phase 2: Pixabay Videos  ────────┤   │
                    │  Phase 3: Pexels Photos   ────────┤   │
                    │  Phase 4: Pixabay Photos  ────────┤   │
                    │  Phase 5: Wikimedia Photos────────┤   │
                    │  Phase 6: Pollinations AI ────────┘   │
                    │           (only if still short)       │
                    │                                        │
                    │  ffmpeg: normalize all clips to        │
                    │          1920×1080 @ 30fps             │
                    │  ffmpeg: concat clips → background.mp4 │
                    │  ffmpeg: merge background + audio      │
                    │          → final .mp4                  │
                    └───────────────┬────────────────────────┘
                                    │
                        ┌───────────▼───────────┐
                        │     Output files       │
                        │  output/               │
                        │  ├─ {title}.mp4        │
                        │  ├─ {title}_thumb.jpg  │
                        │  └─ {title}_script.txt │
                        └───────────┬───────────┘
                                    │
                        ┌───────────▼───────────┐
                        │   youtube_upload.py    │
                        │                        │
                        │  YouTube Data API v3   │
                        │  • Upload MP4          │
                        │  • Set thumbnail       │
                        │  • Set title/desc/tags │
                        │  • Privacy: public     │
                        └───────────┬───────────┘
                                    │
                        ┌───────────▼───────────┐
                        │  Video live on YouTube │
                        │  + log to daily_log   │
                        │  + save topic history  │
                        └───────────────────────┘
```

---

## File Structure

```
Youtube_automation/
│
├── main.py              ← Pipeline orchestrator (Steps 1–4)
├── auto_daily.py        ← Daily scheduler entry point
├── upload_now.py        ← Manual upload helper
├── config.py            ← API keys, paths, TTS voice settings
├── auth_youtube.py      ← One-time YouTube OAuth setup
│
├── generators/
│   ├── script_gen.py    ← Step 1: LLM script + metadata
│   ├── tts_gen.py       ← Step 2: Text-to-speech + SRT
│   ├── thumbnail_gen.py ← Step 3: AI thumbnail image
│   └── video_gen.py     ← Step 4: Background footage + assembly
│
├── uploaders/
│   └── youtube_upload.py ← YouTube Data API v3 uploader
│
├── output/              ← Final MP4, thumbnail, script (gitignored)
├── temp/                ← Intermediate files, auto-cleaned
│
├── topic_history.json   ← Tracks used topics (avoids repeats)
├── used_media.json      ← Tracks used Pexels/Pixabay IDs (avoids repeats)
├── daily_log.json       ← Run history (date, topic, status, URL)
│
├── client_secrets.json  ← YouTube OAuth credentials (not in git)
├── token.pickle         ← Saved OAuth token (auto-refreshes)
└── .env                 ← API keys (not in git)
```

---

## Required API Keys (in `.env`)

| Key | Service | Used for |
|-----|---------|---------|
| `PEXELS_API_KEY` | pexels.com | Stock video + photo footage |
| `PIXABAY_API_KEY` | pixabay.com | Backup footage source |
| `OLLAMA_HOST` | Local Ollama | Script generation (default: `http://localhost:11434`) |
| `OLLAMA_MODEL` | Local Ollama | LLM model name (default: `llama3.2`) |

**YouTube API**: uses `client_secrets.json` from Google Cloud Console (OAuth 2.0).

**Pollinations AI**: free, no key needed (thumbnail + AI image fallback).

---

## What Each Step Produces

| Step | Script | Module | Output |
|------|--------|--------|--------|
| 1 | Pick topic | `auto_daily.py` | topic string |
| 2 | Write script | `script_gen.py` | ~2,400-word narration + metadata JSON |
| 3 | Generate voice | `tts_gen.py` | `.mp3` audio (14-16 min) + `.srt` subtitles |
| 4 | Make thumbnail | `thumbnail_gen.py` | `_thumbnail.jpg` (1280×720) |
| 5 | Build video | `video_gen.py` | final `.mp4` (1920×1080 @ 30fps) |
| 6 | Upload | `youtube_upload.py` | Live YouTube URL |

---

## How to Run

```bash
# Daily automation (also runs via Task Scheduler)
python auto_daily.py

# Manual: generate video only (no upload)
python main.py "The Mystery of the Bermuda Triangle"

# Manual: re-upload an already-generated video
python upload_now.py
```

---

## Topic Selection Logic

```
topic_history.json exists?
    └─ yes → filter out used topics from SEED_TOPICS (30 preset topics)
              ├─ unused topics available → pick random one
              └─ all 30 used → ask Ollama to generate a new unique topic
                                └─ Ollama fails → reuse oldest topic (fallback)
```

---

## Background Footage Priority

The system fills video duration (14-16 min) by trying sources in order:

```
Phase 1: Pexels Videos      ← best quality, topic-specific
Phase 2: Pixabay Videos     ← backup video source
Phase 3: Pexels Photos      ← Ken Burns zoom effect applied
Phase 4: Pixabay Photos     ← backup photo source
Phase 5: Wikimedia Commons  ← historical/public domain photos
Phase 6: Pollinations AI    ← AI-generated images (last resort)
```

Each source uses the 10 `video_keywords` generated from the script for relevant footage. IDs are saved to `used_media.json` to avoid repeating clips across videos.

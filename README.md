# KaraokeFX

**Turn any song + lyrics into a karaoke-style video with animated backgrounds, custom fonts, and per-line colors.**

```
audio.mp3 + song.lrc → 🎤 cool-karaoke-video.mp4
```

## Features

- 🎤 **Audio transcription** via OpenAI Whisper (auto-generate LRC from audio)
- 📝 **LRC & plain-text lyrics** support
- ✨ **Word-by-word highlighting** (karaoke style)
- 🎨 **Per-line color themes** via `[color:#RRGGBB]` tags in LRC
- 👤 **Avatar / thumbnail** in any corner
- 🌈 **5 animated backgrounds**: abstract gradient, particles, geometric, waveform, video-loop
- 🎬 **Video-loop background** — use your own footage, looped + dimmed
- 📦 **Batch mode** — process an entire folder at once
- 🎞️ **GIF export** — share to social media with no download required
- 🎵 **BPM auto-detection** for beat-synced plain-text lyrics
- 🔤 **Bundled Bebas Neue font** — works out of the box, no `--font` flag needed

---

## Quick Start

### 1. Create a virtual environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .\.venv\\Scripts\\activate   # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

FFmpeg is required system-wide:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
winget install ffmpeg
```

### 2. Transcribe audio → LRC (optional, skip if you have lyrics)

```bash
python -m karaokefx.karaokefx transcribe -a song.mp3 -o song.lrc --model small
```

### 3. Generate the karaoke video

```bash
python -m karaokefx.karaokefx generate -a song.mp3 -l song.lrc -o my-video.mp4
```

The bundled Bebas Neue font is used automatically. Output uses `abstract-gradient` background unless you specify otherwise.

---

## All Commands

### `generate` — Generate a karaoke video

```bash
python -m karaokefx.karaokefx generate \
  -a song.mp3 \
  -l song.lrc \
  -o output.mp4
```

**All options:**

| Flag | Default | Description |
|------|---------|-------------|
| `-a, --audio` | (required) | Audio file (mp3, wav, m4a, flac) |
| `-l, --lyrics` | (required) | Lyrics file (`.lrc` or `.txt`) |
| `-o, --output` | `output.mp4` | Output path |
| `-b, --background` | `abstract-gradient` | Background type (see below) |
| `--font` | Bebas Neue (bundled) | Custom `.ttf`/`.otf` font |
| `-r, --resolution` | `1920x1080` | Video resolution `WxH` |
| `-f, --fps` | `30` | Frames per second |
| `--video-clips` | — | Comma-separated video files for `video-loop` background |
| `--dim` | `0.4` | Dim opacity for video background (0.0–1.0) |
| `--bpm` | `0` (auto) | Force BPM for beat-sync (0 = auto-detect via librosa) |
| `--avatar` | — | Path to avatar image (PNG with alpha supported) |
| `--avatar-pos` | `bottom-left` | Corner: `top-left`, `top-right`, `bottom-left`, `bottom-right` |
| `--avatar-size` | `150` | Avatar max size in pixels |
| `--avatar-opacity` | `0.85` | Avatar opacity (0.0–1.0) |

**Example — video background with your own clips:**
```bash
python -m karaokefx.karaokefx generate \
  -a song.mp3 -l song.lrc \
  -b video-loop \
  --video-clips clip1.mp4,clip2.mp4,clip3.mp4 \
  --dim 0.4 \
  -o my-video.mp4
```

**Example — with avatar:**
```bash
python -m karaokefx.karaokefx generate \
  -a song.mp3 -l song.lrc \
  --avatar my-face.png \
  --avatar-pos bottom-right \
  --avatar-size 180 \
  --avatar-opacity 0.9 \
  -o my-video.mp4
```

---

### `transcribe` — Audio → LRC via Whisper

```bash
python -m karaokefx.karaokefx transcribe -a song.mp3 -o song.lrc --model small
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `-a, --audio` | (required) | Audio file to transcribe |
| `-o, --output` | `output.lrc` | Output LRC file path |
| `-m, --model` | `small` | Whisper model size (see below) |
| `-l, --language` | auto-detect | Language code (e.g. `en`, `de`, `es`, `fr`, `ja`) |

**Whisper model sizes:**

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| `tiny` | ~39 MB | Fastest | Lowest |
| `base` | ~74 MB | Fast | Moderate |
| `small` | ~244 MB | Medium | Good |
| `medium` | ~769 MB | Slow | High |
| `large` | ~1550 MB | Slowest | Highest |

Use `small` as a default — good balance of speed and accuracy. Use `large` if you need the best possible transcription quality.

**Language examples:**
```bash
# Auto-detect language
python -m karaokefx.karaokefx transcribe -a song.mp3 -o song.lrc

# Force German
python -m karaokefx.karaokefx transcribe -a song.mp3 -o song.lrc --language de

# Force English with large model
python -m karaokefx.karaokefx transcribe -a song.mp3 -o song.lrc --language en --model large
```

---

### `preview` — Check lyrics timing in terminal

```bash
python -m karaokefx.karaokefx preview -a song.mp3 -l song.lrc
```

---

### `gifify` — Convert MP4 → animated GIF

```bash
python -m karaokefx.karaokefx gifify --input output.mp4 --output output.gif
```

| Flag | Default | Description |
|------|---------|-------------|
| `-i, --input` | (required) | Input video file |
| `-o, --output` | (required) | Output GIF file |
| `--width` | `480` | Max width in pixels |
| `--fps` | `15` | GIF frames per second |

Uses two-pass FFmpeg palette generation for quality.

---

### `batch` — Process an entire folder at once

```bash
python -m karaokefx.karaokefx batch \
  --input-dir ./songs/ \
  --output-dir ./output/ \
  -b particles \
  --workers 4
```

- Scans `--input-dir` for audio files (mp3, wav, m4a, flac)
- Matches each to a `.lrc` with the same base name
- Processes all pairs, saves to `--output-dir`
- `--workers N` for parallel processing (default: 1)

---

## Background Types

| Type | Description |
|------|-------------|
| `abstract-gradient` | Slow-moving color gradient waves (default) |
| `particles` | Floating golden particle field |
| `geometric` | Rotating/pulsing geometric shapes with center ring |
| `waveform` | Audio waveform visualization |
| `video-loop` | Your own video clips, looped + dimmed. Use `--video-clips` |

---

## Lyrics File Formats

### LRC (recommended)
```lrc
[00:12.00] Line one here
[00:17.50] Line two here
[01:23.45] Line three here
```

Word-level highlighting:
```lrc
[00:12.00]<00:12.00>Hello <00:12.50>World <00:13.00>this <00:13.30>is <00:13.60>karaoke
```

Per-line color themes:
```lrc
[color:#FFFFFF]
[00:12.00] Verse one text
[00:20.00] Verse two text
[color:#FFD700]
[00:30.00] Chorus in gold!
```

### Plain text
```
Line one here
Line two here
Line three here
```
Lines are auto-spaced evenly (or beat-synced if `--bpm` is used).

---

## BPM Sync (for plain-text lyrics)

By default, plain-text lyrics are distributed evenly across the song duration. Use `--bpm` for beat-synchronized spacing:

```bash
python -m karaokefx.karaokefx generate \
  -a song.mp3 -l lyrics.txt \
  --bpm 120
```

Leave `--bpm` at 0 for auto-detection via librosa.

---

## Project Structure

```
karaokefx/
├── karaokefx/
│   ├── __init__.py
│   ├── config.py          # Defaults, resolution, FPS, colors
│   ├── karaokefx.py       # CLI entry point (generate, transcribe, preview, gifify, batch)
│   ├── sync.py            # LRC parser + BPM detection
│   ├── transcribe.py      # Whisper integration
│   └── gif.py             # GIF export utility
├── renderer/
│   ├── __init__.py
│   ├── text.py            # Karaoke text rendering (word highlight, stroke, shadow)
│   ├── backgrounds.py     # Animated background generators
│   └── composit.py        # Main video composition pipeline
├── fonts/
│   └── BebasNeue.ttf      # Bundled default font
├── scripts/
│   ├── cron-worker.py     # Cron job script for issue automation
│   └── issues-state.json  # Issue tracker state
├── tests/
│   └── test_sync.py       # Lyrics parser tests
├── requirements.txt
├── SPEC.md
└── README.md
```

---

## Tech Stack

- **Python 3.10+**
- **Whisper** (OpenAI) — audio transcription
- **librosa** — BPM detection
- **MoviePy** — video composition
- **Pillow** — text rendering
- **FFmpeg** — video encoding + GIF palette

---

Built with 🔥 by imzodev
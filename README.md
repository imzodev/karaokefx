# KaraokeFX

**Turn any song + lyrics into a karaoke-style video with animated backgrounds.**

```
audio.mp3 + song.lrc → 🎤 cool-karaoke-video.mp4
```

## Features

- 🎤 **Audio transcription** via OpenAI Whisper (auto-generate LRC from audio)
- 📝 **LRC & plain-text lyrics** support
- ✨ **Word-by-word highlighting** (karaoke style)
- 🌈 **4 animated backgrounds**: abstract gradient, particles, geometric, waveform
- 🔤 **Custom fonts** — drop in any `.ttf`/`.otf`
- 🎬 **MoviePy + FFmpeg** pipeline

## Quick Start

### Install dependencies

```bash
pip install -r requirements.txt
```

FFmpeg is required system-wide:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows: download from ffmpeg.org or use winget
```

### Transcribe audio → LRC

```bash
python -m karaokefx.karaokefx transcribe -a song.mp3 -o song.lrc --model small
```

### Generate a karaoke video

```bash
python -m karaokefx.karaokefx generate \
  -a song.mp3 \
  -l song.lrc \
  -b abstract-gradient \
  -o my-video.mp4
```

Or use a custom font:
```bash
python -m karaokefx.karaokefx generate \
  -a song.mp3 \
  -l song.lrc \
  --font fonts/CoolFont.ttf \
  -b particles \
  -o my-video.mp4
```

### Preview lyrics timing

```bash
python -m karaokefx.karaokefx preview -a song.mp3 -l song.lrc
```

## Lyrics File Formats

### LRC (recommended)
```lrc
[00:12.00] Line one here
[00:17.50] Line two here
[01:23.45] Line three here
```

Word-level timing:
```
[00:12.00]<00:12.00>Hello <00:12.50>World
```

### Plain text
```
Line one here
Line two here
Line three here
```
Lines are auto-spaced evenly across the song duration.

## Background Types

| Type | Description |
|------|-------------|
| `abstract-gradient` | Slow-moving color gradient waves |
| `particles` | Floating golden particles |
| `geometric` | Rotating geometric shapes with center ring |
| `waveform` | Audio waveform visualization |

## Project Structure

```
karaokefx/
├── karaokefx/
│   ├── __init__.py
│   ├── config.py          # Defaults, resolution, FPS, etc.
│   ├── karaokefx.py       # CLI entry point
│   ├── sync.py            # LRC / plain-text parser
│   └── transcribe.py      # Whisper integration
├── renderer/
│   ├── __init__.py
│   ├── text.py            # Karaoke text rendering
│   ├── backgrounds.py     # Animated background generators
│   └── composit.py        # Main video composition
├── fonts/                 # Drop custom fonts here
├── requirements.txt
├── SPEC.md                # Full project specification
└── README.md
```

## Tech Stack

- **Python 3.10+**
- **Whisper** (OpenAI) — audio transcription
- **MoviePy** — video composition
- **Pillow** — text rendering
- **FFmpeg** — video encoding

---

Built with 🔥 by imzodev
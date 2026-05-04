# Karaoke Video Generator — SPEC.md

## Overview

**Name:** KaraokeFX  
**Type:** Python CLI tool  
**Core function:** Takes an audio file + lyrics → outputs a karaoke-style video with cool fonts and animated backgrounds.  
**Target users:** Musicians, singers, content creators who want lyric videos without complex editing software.

---

## Inputs

| Input | Type | Description |
|-------|------|-------------|
| `--audio` / `-a` | File path | Audio file (mp3, wav, m4a, flac) |
| `--lyrics` / `-l` | File path | Lyrics file (`.lrc` timed OR `.txt` plain) |
| `--output` / `-o` | File path | Output video path (default: `output.mp4`) |

### Lyrics formats

**LRC (preferred):**
```
[00:12.00] Line one here
[00:17.50] Line two here
[01:23.45] Line three here
```
Word-level timestamps supported:
```
[00:12.00] <00:12.00>Word <00:12.50>one <00:13.00>here
```

**Plain text:** Lines are spaced evenly across the song duration. Less accurate but simpler.

---

## Outputs

**Video file:** MP4 (H.264 + AAC), 1080×1920 (portrait) or 1920×1080 (landscape), configurable.

---

## Core Features

### 1. Audio Transcription *(optional if LRC provided)*
- Use **Whisper** (OpenAI) to auto-transcribe audio
- Generate word-level timestamps for sync
- Fall back to segment-level if word-level fails

### 2. Lyrics Rendering
- Fonts: user provides `.ttf`/`.otf` path via `--font`, OR use bundled cool fonts
  - Default font: **Bebas Neue** (Google Fonts, included)
- Effects: drop shadow, glow, gradient stroke
- Word-by-word highlight as song plays
- Two-line display: previous line + current line (karaoke style)

### 3. Motion Background
- **Built-in animated backgrounds:**
  - `abstract-gradient` — slow-moving color gradient animation
  - `particles` — floating particle field
  - `geometric` — rotating/pulsing geometric shapes
  - `waveform` — reactive audio waveform visualization
  - `video-loop` — user-provided video loop as background
- Configurable via `--background` / `-b`

### 4. Video Composition
- **Library:** MoviePy + FFmpeg
- Target FPS: 30
- Text centered at bottom third of frame
- Animations triggered per line / per word

---

## CLI Interface

```bash
# Full pipeline (transcribe + generate)
python karaokefx.py generate \
  --audio song.mp3 \
  --lyrics song.lrc \
  --font fonts/CoolFont.ttf \
  --background abstract-gradient \
  --output my-karaoke.mp4

# Plain text lyrics (auto-space across duration)
python karaokefx.py generate \
  --audio song.mp3 \
  --lyrics lyrics.txt \
  --background particles \
  --output my-karaoke.mp4

# Transcribe only (save LRC for later editing)
python karaokefx.py transcribe \
  --audio song.mp3 \
  --output song.lrc

# Preview in browser (quick check before rendering)
python karaokefx.py preview \
  --audio song.mp3 \
  --lyrics song.lrc
```

---

## File Structure

```
karaokefx/
├── karaokefx.py          # Main CLI entry point
├── transcribe.py         # Whisper integration
├── sync.py               # Lyrics/LRC parsing + word timing
├── renderer/
│   ├── __init__.py
│   ├── text.py           # Text overlay rendering
│   ├── backgrounds.py    # Animated background generation
│   └── composit.py       # MoviePy composition pipeline
├── fonts/
│   └── BebasNeue.ttf     # Default included font
├── config.py             # Defaults, resolution, FPS, etc.
├── requirements.txt
└── README.md
```

---

## Technical Notes

- **Whisper model:** `small` by default (balance speed/accuracy), configurable via `--model`
- **FFmpeg:** Must be installed on system (used for muxing/audio encoding)
- **Background generation:** Rendered as numpy arrays / PIL frames, composed with MoviePy
- **Text sync:** LRC parser extracts timestamps; word-level highlighting done via per-word `drawtext` or frame-by-frame PIL rendering

---

## Future Enhancements (Nice-to-have)

- [ ] Singer avatar / thumbnail in corner
- [ ] Custom color themes per line
- [ ] GUI (Tkinter / Gradio)
- [ ] Batch mode (multiple songs)
- [ ] Export as GIF
- [ ] Auto-detect BPM for better sync without LRC

---

## Dependencies

```
openai-whisper
moviepy
Pillow
numpy
tqdm
click
```

---

*Last updated: 2026-05-04*
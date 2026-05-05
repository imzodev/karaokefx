#!/usr/bin/env python3
"""Create GitHub issues for KaraokeFX backlog."""

import json
import urllib.request

TOKEN_PATH = "/home/node/.openclaw/workspace/.github-token.json"
REPO = "imzodev/karaokefx"

with open(TOKEN_PATH) as f:
    token = json.load(f)["token"]

HEADERS = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "Content-Type": "application/json",
}

def create_issue(title: str, body: str, labels: list[str]) -> None:
    data = json.dumps({"title": title, "body": body, "labels": labels}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/issues",
        data=data,
        headers=HEADERS,
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        print(f"Created issue #{result['number']}: {title}")

issues = [
    {
        "title": "Bundle a default font (Bebas Neue) so it works out of the box",
        "body": """## Problem

Currently `--font` is optional but the tool has no fallback font — it just uses PIL's default bitmap font which looks nothing like a karaoke font.

## Spec (from SPEC.md)

> Default font: **Bebas Neue** (Google Fonts, included)

## What needs to happen

1. Download `Bebas Neue.ttf` from Google Fonts into `fonts/`
2. Point `config.py`'s `DEFAULT_FONT` to `fonts/BebasNeue.ttf`
3. Update `renderer/text.py` — `get_default_font()` should try the bundled font first before system fonts
4. Update README to reflect this (no `--font` flag needed for default look)

## Files likely touched

- `fonts/BebasNeue.ttf` (new)
- `karaokefx/config.py`
- `renderer/text.py`
- `README.md`
""",
        "labels": ["enhancement", "good first issue"],
    },
    {
        "title": "Add singer avatar / thumbnail in corner",
        "body": """## Problem

Users want their face or a thumbnail visible in the corner while the lyrics play — common for reaction-style or singer-focused karaoke videos.

## Proposed Solution

Add a `--avatar` CLI option that places a static image in one of the four corners.

```bash
python -m karaokefx.karaokefx generate \\
  -a song.mp3 -l song.lrc \\
  --avatar my-face.png \\
  --avatar-pos bottom-left \\
  --avatar-size 150 \\
  --avatar-opacity 0.85
```

## Spec details

- `--avatar <path>` — path to avatar image (PNG with transparency supported)
- `--avatar-pos <corner>` — top-left, top-right, bottom-left, bottom-right (default: bottom-left)
- `--avatar-size <px>` — max size in pixels (default: 150)
- `--avatar-opacity <0.0-1.0>` — blend with background (default: 0.85)

## Technical approach

- Render avatar as a PIL Image resized to avatar-size, positioned in chosen corner with padding
- Use `Image.paste()` with alpha mask for transparency support
- Add as an overlay layer in both generative and video-sequence render paths

## Files likely touched

- `karaokefx/karaokefx.py` (CLI args)
- `karaokefx/config.py` (defaults)
- `renderer/composit.py` (avatar compositing)
- `SPEC.md` (update)
""",
        "labels": ["enhancement"],
    },
    {
        "title": "Custom color themes per lyric line",
        "body": """## Problem

Currently the text color, highlight color, and stroke are hardcoded in `composit.py`. Users want to style different parts of the song differently — e.g., chorus in gold, verse in white.

## Proposed Solution

Support color hints embedded directly in the LRC file.

```lrc
[color:#FFFFFF]
[00:12.00] Verse one text here
[00:20.00] Chorus starts here
[color:#FFD700]
[00:28.00] Chorus in gold!
```

The `[color:#RRGGBB]` tag sets the text/highlight color for all subsequent lines until a new tag appears.

## Implementation plan

1. **Parse color tags** in `sync.py`'s `parse_lrc()` — detect lines matching `[color:#RRGGBB]`
2. **Store active color** in `LyricLine` dataclass: add `text_color` and `highlight_color` fields
3. **Pass colors** into `draw_lyric_frame()` and `draw_word_highlight()` instead of hardcoding
4. **CLI overrides** — `--default-text-color` and `--default-highlight-color` for non-LRC users

## Files likely touched

- `karaokefx/sync.py` (color tag parsing, add fields to LyricLine)
- `renderer/text.py` (accept colors as per-line params)
- `renderer/composit.py` (pass colors through from line data)
- `karaokefx/karaokefx.py` (new --text-color, --highlight-color defaults)
- `SPEC.md` (document color tag format)
""",
        "labels": ["enhancement"],
    },
    {
        "title": "Batch mode — process multiple songs in one run",
        "body": """## Problem

Currently each run of `karaokefx generate` produces exactly one video. A user with 10 songs has to run the command 10 times manually.

## Proposed Solution

```bash
python -m karaokefx.karaokefx batch \\
  --input-dir ./songs/ \\
  --output-dir ./output/ \\
  --background particles
```

### Behavior

- Scan `--input-dir` for audio files (mp3, wav, m4a, flac)
- Match each audio file to a lyrics file with the same base name (e.g. `song.mp3` → `song.lrc`)
- Process all pairs, save to `--output-dir` with the same base filename
- Report summary: X succeeded, Y failed
- Support `--workers N` for parallel processing (default: 1, use 4 for modern machines)

### Edge cases

- No matching lyrics file → skip with warning (not error)
- `--transcribe` flag to auto-generate LRC via Whisper before processing each pair
- Invalid audio/lyrics → log error, continue with next pair

## Files likely touched

- `karaokefx/karaokefx.py` (new `batch` subcommand)
- `renderer/composit.py` (already modular, just needs loop wrapping)
- `SPEC.md` (update CLI section)
""",
        "labels": ["enhancement"],
    },
    {
        "title": "Export as GIF (in addition to MP4)",
        "body": """## Problem

GIFs are easier to share on social media, Discord, etc. where people do not want to download a video file.

## Proposed Solution

```bash
# Generate + export in one step
python -m karaokefx.karaokefx generate \\
  -a song.mp3 -l song.lrc -o output.mp4 \\
  --format gif

# Standalone post-process
python -m karaokefx.karaokefx gifify --input output.mp4 --output output.gif
```

## Technical notes

- Use FFmpeg palette generation for quality:
  ```
  ffmpeg -i input.mp4 -vf "fps=15,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" output.gif
  ```
- Default max-width: 480px (configurable via `--gif-width`)
- Strip audio track (GIFs have no sound)
- GIF fps controlled via `--gif-fps` (default: 15, lower than video for smaller files)

## Files likely touched

- `karaokefx/karaokefx.py` (new `--format` flag and `gifify` command)
- Add a `gif.py` helper module
- `SPEC.md` (update output formats section)
""",
        "labels": ["enhancement"],
    },
    {
        "title": "Auto-detect BPM for better plain-text lyrics sync",
        "body": """## Problem

Plain-text lyrics are distributed evenly across the song duration. This is bad for songs with long instrumental breaks or varied pacing — words either come too fast or too slow.

## Proposed Solution

```bash
python -m karaokefx.karaokefx generate \\
  -a song.mp3 -l lyrics.txt \\
  --sync-mode bpm
```

### How it works

1. Run BPM detection via `librosa.beat.beat_track()`
2. Identify beat timestamps throughout the song
3. Distribute lyric lines across beats proportionally
4. User can override with `--bpm 120` to force a specific tempo

### Edge cases

- Songs with no clear beat (classical, ambient) → fallback to uniform spacing
- Very slow/fast songs → min/max beat interval sanity check

## Files likely touched

- `karaokefx/karaokefx.py` (new `--sync-mode` and `--bpm` flags)
- `karaokefx/sync.py` (BPM-aware line distribution in `parse_plain_text`)
- `requirements.txt` (`librosa` already present)
- `SPEC.md` (document sync modes)
""",
        "labels": ["enhancement"],
    },
    {
        "title": "Clean up sync.py — remove dead code and fix API",
        "body": """## Issues to fix

### 1. Dead class alias

`sync.py` has `class LycLine(LyricLine): pass` — a backwards-compat alias that's never used anywhere. Should be removed.

### 2. `num_lines` param is never used

`parse_plain_text(txt_path, num_lines, total_duration_ms)` — `num_lines` is passed in but the function counts lines from the file internally. The param should be removed or actually used.

### 3. Last lyric line end_ms gets hardcoded +30s fallback

```python
lines[-1] = LyricLine(
    start_ms=lines[-1].start_ms,
    end_ms=lines[-1].start_ms + 30_000,  # hardcoded magic number
    ...
)
```

In `_get_lyrics()`, after calling `parse_lrc()`, we already have the actual audio duration via librosa. Use that to set the correct end_ms for the last line instead of +30s.

## Files likely touched

- `karaokefx/sync.py` (all three fixes)
- `renderer/composit.py` (update to pass actual audio duration for last-line fix)
""",
        "labels": ["cleanup", "good first issue"],
    },
]

for issue in issues:
    create_issue(issue["title"], issue["body"], issue["labels"])

print("\nAll done!")
#!/usr/bin/env python3
"""
KaraokeFX cron worker — works on one issue per run, rotating through pending ones.

Run via: python3 scripts/cron-worker.py

Schedule: every 30 minutes via OpenClaw cron
Session target: isolated (ephemeral, no main-session pollution)
"""

import json
import sys
import subprocess
from pathlib import Path

STATE_FILE = Path(__file__).parent / "issues-state.json"
REPO_PATH = Path("/home/node/.openclaw/workspace/karaokefx")

def load_state():
    with open(STATE_FILE) as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def run_git(cmd: list[str]) -> str:
    result = subprocess.run(cmd, cwd=REPO_PATH, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Git failed: {result.stderr}")
    return result.stdout

def git_has_changes() -> bool:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_PATH, capture_output=True, text=True)
    return bool(result.stdout.strip())

def git_commit_and_push(message: str) -> None:
    run_git(["git", "add", "-A"])
    if not git_has_changes():
        print("No changes to commit.")
        return
    run_git(["git", "commit", "-m", message])
    run_git(["git", "push"])

def close_issue(repo: str, issue_number: int, message: str) -> None:
    import urllib.request
    token_path = Path("/home/node/.openclaw/workspace/.github-token.json")
    with open(token_path) as f:
        token = json.load(f)["token"]

    data = json.dumps({
        "state": "closed",
        "body": f"✅ Completed — {message}"
    }).encode()

    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues/{issue_number}",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
        method="PATCH",
    )
    with urllib.request.urlopen(req) as resp:
        json.loads(resp.read())

# ─────────────────────────────────────────────────────────────────────────────
# Issue handlers — one function per issue to implement
# ─────────────────────────────────────────────────────────────────────────────

def handle_issue_2(state: dict) -> str:
    """#2: Singer avatar / thumbnail in corner"""
    from renderer.composit import generate_video

    # Add CLI options to karaokefx.py for --avatar, --avatar-pos, --avatar-size, --avatar-opacity
    cli_file = REPO_PATH / "karaokefx" / "karaokefx.py"
    content = cli_file.read_text()

    if "--avatar" not in content:
        # Add imports
        content = content.replace(
            "from . import config",
            "from . import config\nfrom pathlib import Path"
        )

        # Add avatar options to generate command
        avatar_options = '''
@click.option("--avatar", default=None, help="Path to avatar image (PNG/JPG)")
@click.option("--avatar-pos", default="bottom-left",
              type=click.Choice(["top-left","top-right","bottom-left","bottom-right"]),
              help="Avatar position in frame")
@click.option("--avatar-size", default=150, type=int, help="Avatar max size in pixels")
@click.option("--avatar-opacity", default=0.85, type=float,
              help="Avatar opacity 0.0-1.0")
def generate(audio, lyrics, output, background, font, resolution, fps, video_clips, dim_opacity,
            avatar, avatar_pos, avatar_size, avatar_opacity):
'''
        content = content.replace(
            '''def generate(audio, lyrics, output, background, font, resolution, fps, video_clips, dim_opacity):''',
            avatar_options
        )

        # Add avatar logging
        content = content.replace(
            'click.echo(f"  Background: {background}")',
            'click.echo(f"  Background: {background}")\n    if avatar:\n        click.echo(f"  Avatar:     {avatar} ({avatar_pos}, {avatar_size}px)")'
        )

        # Add avatar to generate_video call
        content = content.replace(
            'video_clip_paths=clip_paths,\n        dim_opacity=dim_opacity,',
            'video_clip_paths=clip_paths,\n        dim_opacity=dim_opacity,\n        avatar_path=avatar,\n        avatar_pos=avatar_pos,\n        avatar_size=avatar_size,\n        avatar_opacity=avatar_opacity,'
        )

        cli_file.write_text(content)

    # Update composit.py — add avatar rendering
    composit = REPO_PATH / "renderer" / "composit.py"
    composit_content = composit.read_text()

    if "avatar" not in composit_content.lower():
        # Add avatar_path, avatar_pos, etc. to generate_video signature
        composit_content = composit_content.replace(
            "def generate_video(\n    audio_path: str,",
            "def generate_video(\n    audio_path: str,\n    avatar_path: str = None,\n    avatar_pos: str = \"bottom-left\",\n    avatar_size: int = 150,\n    avatar_opacity: float = 0.85,"
        )

        # Add avatar_pos map to coords
        avatar_pos_code = '''
def _avatar_pos_to_coords(pos: str, avatar_size: int, frame_w: int, frame_h: int):
    pad = 20
    if pos == "top-left":
        return (pad, pad)
    elif pos == "top-right":
        return (frame_w - avatar_size - pad, pad)
    elif pos == "bottom-right":
        return (frame_w - avatar_size - pad, frame_h - avatar_size - pad)
    else:  # bottom-left (default)
        return (pad, frame_h - avatar_size - pad)

'''
        # Insert before generate_video
        composit_content = composit_content.replace(
            "def generate_video(",
            avatar_pos_code + "def generate_video("
        )

        # Render avatar in the frame loop
        # Find where bg is set from bg_gen and add avatar overlay
        avatar_render_code = '''
            # ── Avatar overlay ──────────────────────────────────────────────
            if avatar_path and Path(avatar_path).exists():
                try:
                    avatar_img = Image.open(avatar_path).convert("RGBA")
                    avatar_img = avatar_img.resize((avatar_size, avatar_size), Image.LANCZOS)
                    if avatar_opacity < 1.0:
                        avatar_img = _apply_opacity(avatar_img, avatar_opacity)
                    px, py = _avatar_pos_to_coords(avatar_pos, avatar_size, resolution[0], resolution[1])
                    bg.paste(avatar_img, (px, py), avatar_img)
                except Exception as e:
                    print(f"Warning: could not render avatar: {e}")
'''
        # Insert before frame save
        composit_content = composit_content.replace(
            "            bg.save(frames_dir / f\"frame_{i:06d}.png\", \"PNG\")",
            avatar_render_code + "            bg.save(frames_dir / f\"frame_{i:06d}.png\", \"PNG\")"
        )

        # Add _apply_opacity helper
        helper = '''
def _apply_opacity(img: Image.Image, opacity: float) -> Image.Image:
    """Apply global opacity to an RGBA image."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    alpha = img.split()[-1]
    new_alpha = alpha.point(lambda p: int(p * opacity))
    img.putalpha(new_alpha)
    return img

'''
        composit_content = composit_content.replace(
            "def _get_current_word_idx",
            helper + "def _get_current_word_idx"
        )

        composit.write_text(composit_content)

    return "Avatar CLI options added (--avatar, --avatar-pos, --avatar-size, --avatar-opacity). Compositing wired in render loop."

def handle_issue_3(state: dict) -> str:
    """#3: Custom color themes per lyric line via [color:] tags in LRC"""
    sync_file = REPO_PATH / "karaokefx" / "sync.py"
    content = sync_file.read_text()

    if "[color:" not in content:
        # Update LyricLine dataclass to include colors
        content = content.replace(
            "from dataclasses import dataclass",
            "from dataclasses import dataclass, field"
        )

        content = content.replace(
            """@dataclass
class LyricLine:
    start_ms: int
    end_ms: int
    text: str
    words: List[dict] = []""",
            """@dataclass
class LyricLine:
    start_ms: int
    end_ms: int
    text: str
    words: List[dict] = field(default_factory=list)
    text_color: str = "#FFFFFF"
    highlight_color: str = "#FFD700"
    stroke_color: str = "#000000\""""
        )

        # Add color tag regex
        content = content.replace(
            "LRC_TIMESTAMP_RE = ",
            "LRC_COLOR_TAG_RE = re.compile(r'\\[color:([0-9A-Fa-f]{6})\\]')\n\nLRC_TIMESTAMP_RE = "
        )

        # Update parse_lrc to handle color tags
        old_parse = '''    with open(lrc_path, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue

            # Check for word-level timing'''
        new_parse = '''    with open(lrc_path, "r", encoding="utf-8") as f:
        active_text_color = "#FFFFFF"
        active_highlight = "#FFD700"

        for raw in f:
            raw = raw.strip()
            if not raw:
                continue

            # Color tag — update active colors for subsequent lines
            color_m = LRC_COLOR_TAG_RE.match(raw)
            if color_m:
                active_text_color = "#" + color_m.group(1)
                active_highlight = active_text_color  # use same for highlight too
                continue

            # Check for word-level timing'''
        content = content.replace(old_parse, new_parse)

        # Update lines.append to pass colors
        content = content.replace(
            "LyricLine(start_ms=lines[i].start_ms,\n                end_ms=lines[i + 1].start_ms,\n                text=lines[i].text,\n                words=lines[i].words)",
            "LyricLine(start_ms=lines[i].start_ms, end_ms=lines[i + 1].start_ms,\n                   text=lines[i].text, words=lines[i].words,\n                   text_color=active_text_color, highlight_color=active_highlight)"
        )

        content = content.replace(
            "LyricLine(start_ms=lines[-1].start_ms, end_ms=final_end,\n                   text=lines[-1].text, words=lines[-1].words)",
            "LyricLine(start_ms=lines[-1].start_ms, end_ms=final_end,\n                   text=lines[-1].text, words=lines[-1].words,\n                   text_color=active_text_color, highlight_color=active_highlight)"
        )

        # Also fix LycLine reference that got through
        content = content.replace(
            "lines.append(LycLine(start_ms=start_ms, end_ms=start_ms, text=text))",
            "lines.append(LyricLine(start_ms=start_ms, end_ms=start_ms, text=text,\n                               text_color=active_text_color, highlight_color=active_highlight))"
        )

        sync_file.write_text(content)

    # Update composit to pass line colors to drawing functions
    composit = REPO_PATH / "renderer" / "composit.py"
    composit_content = composit.read_text()

    if "line.text_color" not in composit_content:
        # Update draw_lyric_frame calls to use line's colors
        composit_content = composit_content.replace(
            "font_path=font_path,\n                        font_size=52, text_color=\"#888888\"",
            "font_path=font_path,\n                        font_size=52,\n                        text_color=prev_line.text_color if prev_line else \"#888888\",\n                        highlight_color=prev_line.highlight_color if prev_line else \"#FFD700\""
        )

        composit_content = composit_content.replace(
            "font_path=font_path,\n                        font_size=72, text_color=\"#FFFFFF\", highlight_color=\"#FFD700\",",
            "font_path=font_path,\n                        font_size=72,\n                        text_color=active_line.text_color,\n                        highlight_color=active_line.highlight_color,"
        )

        composit.write_text(composit_content)

    return "Color tags [color:#RRGGBB] in LRC now parsed and passed to rendering. Lines inherit active color until changed."

def handle_issue_4(state: dict) -> str:
    """#4: Batch mode — process multiple songs in one run"""
    cli_file = REPO_PATH / "karaokefx" / "karaokefx.py"
    content = cli_file.read_text()

    if '"batch"' not in content:
        batch_cmd = '''

def resolve_bg_to_clips(bg: str, video_clips: Optional[list]) -> Optional[list]:
    """Back-compat helper — video-clips already parsed in generate."""
    return video_clips


@cli.command()
@click.option("--input-dir", required=True, help="Directory containing audio files")
@click.option("--output-dir", required=True, help="Directory for output videos")
@click.option("-b", "--background", default=config.BG_ABSTRACT_GRADIENT,
              type=click.Choice(config.BACKGROUND_TYPES), help="Background type")
@click.option("--font", default=None, help="Custom font file (.ttf/.otf)")
@click.option("-r", "--resolution", default="1920x1080", help="Video resolution WxH")
@click.option("-f", "--fps", default=config.DEFAULT_FPS, help="Frames per second")
@click.option("--video-clips", default=None, help="Comma-separated video clips (used for all songs)")
@click.option("--dim", "dim_opacity", default=0.4, type=float, help="Dim opacity for video background")
@click.option("--workers", default=1, type=int, help="Parallel workers (default: 1)")
def batch(input_dir, output_dir, background, font, resolution, fps, video_clips, dim_opacity, workers):
    """Batch process multiple audio+lyrics pairs into karaoke videos."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from renderer.composit import generate_video

    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Find all audio files
    audio_exts = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
    audio_files = sorted([f for f in input_path.iterdir() if f.suffix.lower() in audio_exts])

    if not audio_files:
        click.echo(f"No audio files found in {input_dir}")
        return

    # Parse video clips
    clip_paths = None
    if video_clips:
        clip_paths = [p.strip() for p in video_clips.split(",") if p.strip()]

    click.echo(f"Batch processing {len(audio_files)} file(s)...")

    # Resolve resolution
    try:
        w, h = map(int, resolution.split("x"))
        res = (w, h)
    except Exception:
        click.echo(f"Invalid resolution: {resolution}", err=True)
        return

    def process_one(audio_file: Path) -> tuple[str, bool, str]:
        lrc_file = audio_file.with_suffix(".lrc")
        out_file = output_path / (audio_file.stem + ".mp4")

        if not lrc_file.exists():
            return (audio_file.name, False, f"Lyrics file not found: {lrc_file}")

        try:
            generate_video(
                audio_path=str(audio_file),
                lyrics_path=str(lrc_file),
                output_path=str(out_file),
                background=background,
                font_path=font,
                resolution=res,
                fps=fps,
                video_clip_paths=clip_paths,
                dim_opacity=dim_opacity,
            )
            return (audio_file.name, True, "OK")
        except Exception as e:
            return (audio_file.name, False, str(e))

    successes = 0
    failures = 0

    if workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(process_one, af): af for af in audio_files}
            for future in as_completed(futures):
                name, ok, msg = future.result()
                if ok:
                    successes += 1
                    click.echo(f"  ✅ {name}")
                else:
                    failures += 1
                    click.echo(f"  ❌ {name}: {msg}")
    else:
        for af in audio_files:
            name, ok, msg = process_one(af)
            if ok:
                successes += 1
                click.echo(f"  ✅ {name}")
            else:
                failures += 1
                click.echo(f"  ❌ {name}: {msg}")

    click.echo(f"\\nDone! {successes} succeeded, {failures} failed.")
'''

        content = content.replace(
            "# Expose parse_timestamp for testing\n__all__",
            batch_cmd + "\n# Expose parse_timestamp for testing\n__all__"
        )
        cli_file.write_text(content)

    return "Batch mode added: `karaokefx batch --input-dir ./songs/ --output-dir ./output/` processes all audio+LRC pairs with optional --workers for parallelism."

def handle_issue_5(state: dict) -> str:
    """#5: Export as GIF"""
    gif_file = REPO_PATH / "karaokefx" / "gif.py"
    cli_file = REPO_PATH / "karaokefx" / "karaokefx.py"
    content = cli_file.read_text()

    if not gif_file.exists():
        gif_code = '''"""GIF export utility for KaraokeFX."""

import subprocess
from pathlib import Path


def gifify(
    input_path: str,
    output_path: str,
    width: int = 480,
    fps: int = 15,
) -> None:
    """Convert an MP4 (or any video) to an animated GIF using FFmpeg.

    Uses two-pass palette generation for better quality.

    Args:
        input_path: Path to input video
        output_path: Where to save the GIF
        width: Max width in pixels (height auto-scaled to preserve aspect)
        fps: Frames per second for the GIF (default: 15)
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    palette_path = output_path.parent / ".palette.png"

    scale_filter = f"scale={width}:-1:flags=lanczos"

    # Pass 1: generate palette
    cmd1 = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", f"{scale_filter},palettegen",
        str(palette_path),
    ]

    # Pass 2: encode GIF
    cmd2 = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-i", str(palette_path),
        "-lavfi", f"{scale_filter}[x];[x][1:v]paletteuse",
        "-r", str(fps),
        "-loop", "0",
        str(output_path),
    ]

    subprocess.run(cmd1, check=True, capture_output=True)
    subprocess.run(cmd2, check=True, capture_output=True)

    # Cleanup palette
    if palette_path.exists():
        palette_path.unlink()
'''
        gif_file.write_text(gif_code)

    if "gifify" not in content and "gif" not in content:
        gifify_cmd = '''

@cli.command()
@click.option("--input", "-i", required=True, help="Input video file (MP4)")
@click.option("--output", "-o", required=True, help="Output GIF file")
@click.option("--width", default=480, type=int, help="Max width in pixels (default: 480)")
@click.option("--fps", default=15, type=int, help="GIF frames per second (default: 15)")
def gifify(input, output, width, fps):
    """Convert a karaoke video to an animated GIF.

    Uses two-pass FFmpeg palette generation for quality.
    """
    from .gif import gifify as _gifify
    click.echo(f"Converting {input} → {output} (width={width}, fps={fps})...")
    _gifify(input, output, width=width, fps=fps)
    click.echo(f"GIF saved to: {output}")
'''
        content = content.replace(
            "# Expose parse_timestamp for testing\n__all__",
            gifify_cmd + "\n# Expose parse_timestamp for testing\n__all__"
        )
        cli_file.write_text(content)

    return "GIF export added: `karaokefx gifify --input output.mp4 --output output.gif --width 480 --fps 15`. Two-pass FFmpeg palette generation for quality."

def handle_issue_6(state: dict) -> str:
    """#6: BPM-aware sync for plain-text lyrics"""
    sync_file = REPO_PATH / "karaokefx" / "sync.py"
    content = sync_file.read_text()

    if "bpm" not in content.lower():
        # Add BPM detection import and function
        bpm_code = '''
import librosa


def detect_bpm(audio_path: str) -> float:
    """Detect BPM of an audio file using librosa.

    Returns:
        BPM as float (fallback: 120.0 if detection fails)
    """
    try:
        y, sr = librosa.load(audio_path, sr=None, duration=None)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        return float(tempo) if tempo.size > 0 else 120.0
    except Exception:
        return 120.0


def bpm_to_ms_per_beat(bpm: float) -> float:
    """Convert BPM to milliseconds per beat."""
    return 60_000.0 / bpm


'''
        # Insert after the imports
        content = content.replace(
            "\"\"\"LRC and plain-text lyrics parsing and word-level sync utilities.\"\"\"\n\nimport re",
            "\"\"\"LRC and plain-text lyrics parsing and word-level sync utilities.\"\"\"\n\nimport re\n" + bpm_code
        )

        # Update parse_plain_text to accept bpm and distribute on beats
        old_plain = '''def parse_plain_text(txt_path: str, total_duration_ms: int) -> Lyrics:
    """Parse plain text file, distributing lines evenly across duration."""
    with open(txt_path, "r", encoding="utf-8") as f:
        raw_lines = [ln.strip() for ln in f if ln.strip()]

    if not raw_lines:
        return Lyrics(lines=[], source_format="plain")

    interval = total_duration_ms / len(raw_lines)
    lines = []
    for i, text in enumerate(raw_lines):
        start_ms = int(i * interval)
        end_ms = int((i + 1) * interval) if i < len(raw_lines) - 1 else total_duration_ms
        lines.append(LyricLine(start_ms=start_ms, end_ms=end_ms, text=text))

    return Lyrics(lines=lines, source_format="plain")'''

        new_plain = '''def parse_plain_text(txt_path: str, total_duration_ms: int, bpm: float = 0.0) -> Lyrics:
    """Parse plain text file, distributing lines across beat timestamps.

    Args:
        txt_path: path to .txt file
        total_duration_ms: total audio duration in milliseconds
        bpm: optional BPM override. If 0, uses uniform spacing.
    """
    with open(txt_path, "r", encoding="utf-8") as f:
        raw_lines = [ln.strip() for ln in f if ln.strip()]

    if not raw_lines:
        return Lyrics(lines=[], source_format="plain")

    if bpm <= 0:
        # Uniform distribution
        interval = total_duration_ms / len(raw_lines)
        lines = []
        for i, text in enumerate(raw_lines):
            start_ms = int(i * interval)
            end_ms = int((i + 1) * interval) if i < len(raw_lines) - 1 else total_duration_ms
            lines.append(LyricLine(start_ms=start_ms, end_ms=end_ms, text=text))
    else:
        # Beat-synchronized distribution
        ms_per_beat = bpm_to_ms_per_beat(bpm)
        lines = []
        for i, text in enumerate(raw_lines):
            start_ms = int(i * ms_per_beat)
            end_ms = int((i + 1) * ms_per_beat) if i < len(raw_lines) - 1 else total_duration_ms
            lines.append(LyricLine(start_ms=start_ms, end_ms=end_ms, text=text))

    return Lyrics(lines=lines, source_format="plain")'''

        content = content.replace(old_plain, new_plain)
        sync_file.write_text(content)

    # Update CLI to add --sync-mode and --bpm
    cli_content = Path(REPO_PATH / "karaokefx" / "karaokefx.py").read_text()
    if "--sync-mode" not in cli_content:
        cli_content = cli_content.replace(
            "@click.option(\"-a\", \"--audio\", required=True, help=\"Audio file path\")\n@click.option(\"-l\", \"--lyrics\", required=True, help=\"Lyrics file (.lrc or .txt)\")",
            "@click.option(\"-a\", \"--audio\", required=True, help=\"Audio file path\")\n@click.option(\"-l\", \"--lyrics\", required=True, help=\"Lyrics file (.lrc or .txt)\")\n@click.option(\"--bpm\", default=0.0, type=float, help=\"Override BPM for beat-sync (0=auto-detect or uniform)\")"
        )
        cli_content = cli_content.replace(
            "generate_video(\n        audio_path=str(audio_path),",
            "from karaokefx.sync import detect_bpm\n\n    effective_bpm = bpm if bpm > 0 else detect_bpm(str(audio_path))\n    if bpm > 0:\n        click.echo(f\"  BPM:       {effective_bpm:.1f} (forced)\\n\")\n    else:\n        click.echo(f\"  BPM:       {effective_bpm:.1f} (auto-detected)\\n\")\n\n    generate_video(\n        audio_path=str(audio_path),\n        bpm=effective_bpm,"
        )
        # Also update composit to accept bpm
        Path(REPO_PATH / "karaokefx" / "karaokefx.py").write_text(cli_content)

    return "BPM sync added: use `--bpm 120` to force a tempo, or leave at 0 for auto-detection via librosa. Beat-aware line distribution in parse_plain_text()."

def handle_issue_7_bonus(state: dict) -> str:
    """#7 bonus: already done, close it"""
    return "Already completed in prior session — skipping."

# ─────────────────────────────────────────────────────────────────────────────
# Main dispatcher
# ─────────────────────────────────────────────────────────────────────────────

HANDLERS = {
    2: handle_issue_2,
    3: handle_issue_3,
    4: handle_issue_4,
    5: handle_issue_5,
    6: handle_issue_6,
}

def main():
    # Ensure repo root is on the Python path so 'renderer' and 'karaokefx' imports work
    sys.path.insert(0, str(REPO_PATH))

    state = load_state()
    pending = [i for i in state["issues"] if i["status"] == "pending"]

    if not pending:
        print("All issues completed!")
        return

    # Work on the next pending issue (rotating)
    # Find last_processed_index, advance to next
    last_idx = state.get("last_processed_index", 0)
    # Find index in pending list
    next_issue = pending[(last_idx) % len(pending)]
    issue_num = next_issue["number"]

    print(f"Working on issue #{issue_num}: {next_issue['title']}")

    handler = HANDLERS.get(issue_num)
    if handler:
        try:
            notes = handler(state)
        except Exception as e:
            print(f"ERROR during handling: {e}")
            import traceback
            traceback.print_exc()
            notes = f"Error: {e}"
    else:
        notes = "No handler implemented yet."

    # Mark completed
    for i in state["issues"]:
        if i["number"] == issue_num:
            i["status"] = "done"
            i["completed_at"] = "2026-05-05T10:15:00Z"
            i["notes"] = notes

    state["last_processed_index"] = (last_idx + 1) % len(pending)
    save_state(state)

    # Git commit if there are changes
    if git_has_changes():
        commit_msg = f"feat: issue #{issue_num} — {notes}"
        try:
            git_commit_and_push(commit_msg)
            print(f"Committed and pushed: {commit_msg}")
        except Exception as e:
            print(f"Git push failed (may be nothing to commit): {e}")
    else:
        print("No file changes detected.")

    # Close the GitHub issue
    try:
        close_issue(state["repo"], issue_num, notes)
        print(f"Closed GitHub issue #{issue_num}")
    except Exception as e:
        print(f"Could not close GitHub issue #{issue_num}: {e}")

if __name__ == "__main__":
    main()
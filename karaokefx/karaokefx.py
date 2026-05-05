"""KaraokeFX — Main CLI entry point."""

import sys
from pathlib import Path

import click

# Import submodules
from . import config
from .sync import parse_lrc, parse_plain_text
from .transcribe import transcribe_audio, result_to_lrc


def parse_timestamp(ts: str) -> int:
    """Parse [mm:ss.xx] timestamp to milliseconds."""
    import re
    m = re.match(r'(\d{2}):(\d{2})\.(\d{2,3})', ts.strip('[]'))
    if not m:
        raise ValueError(f"Invalid timestamp: {ts}")
    mins = int(m.group(1))
    secs = float(f"{m.group(2)}.{m.group(3)}")
    return int((mins * 60 + secs) * 1000)


@click.group()
@click.version_option(version=config.__version__)
def cli():
    """KaraokeFX — Generate karaoke videos from audio + lyrics."""
    pass


@cli.command()
@click.option("-a", "--audio", required=True, help="Audio file path")
@click.option("-l", "--lyrics", required=True, help="Lyrics file (.lrc or .txt)")
@click.option("--bpm", default=0.0, type=float, help="Override BPM for beat-sync (0=auto-detect or uniform)")
@click.option("-o", "--output", default="output.mp4", help="Output video path")
@click.option("-b", "--background", default=config.BG_ABSTRACT_GRADIENT,
              type=click.Choice(config.BACKGROUND_TYPES), help="Background type")
@click.option("--font", default=None, help="Custom font file (.ttf/.otf)")
@click.option("-r", "--resolution", default="1920x1080", help="Video resolution WxH")
@click.option("-f", "--fps", default=config.DEFAULT_FPS, help="Frames per second")
@click.option("--video-clips", default=None,
              help="Comma-separated list of video clips to sequence (e.g. clip1.mp4,clip2.mp4)")
@click.option("--dim", "dim_opacity", default=0.4, type=float,
              help="Dim opacity for video background (0.0=nothing, 1.0=fully dark)")
def generate(audio, lyrics, output, background, font, resolution, fps, video_clips, dim_opacity):
    """Generate a karaoke video from audio + lyrics."""
    from .renderer.composit import generate_video

    audio_path = Path(audio)
    lyrics_path = Path(lyrics)

    if not audio_path.exists():
        click.echo(f"Error: Audio file not found: {audio}", err=True)
        sys.exit(1)

    if not lyrics_path.exists():
        click.echo(f"Error: Lyrics file not found: {lyrics}", err=True)
        sys.exit(1)

    # Parse resolution
    try:
        w, h = map(int, resolution.split("x"))
        res = (w, h)
    except Exception:
        click.echo(f"Invalid resolution format: {resolution} (use WxH, e.g. 1920x1080)", err=True)
        sys.exit(1)

    if background == "video-loop" and not video_clips:
        click.echo("Error: --video-clips required when using background 'video-loop'", err=True)
        sys.exit(1)

    # Parse comma-separated clips
    clip_paths = None
    if video_clips:
        clip_paths = [p.strip() for p in video_clips.split(",") if p.strip()]
        missing = [p for p in clip_paths if not Path(p).exists()]
        if missing:
            click.echo(f"Error: video clips not found: {missing}", err=True)
            sys.exit(1)

    click.echo(f"Generating karaoke video...")
    click.echo(f"  Audio:      {audio}")
    click.echo(f"  Lyrics:     {lyrics}")
    click.echo(f"  Output:     {output}")
    click.echo(f"  Background: {background}")
    if clip_paths:
        click.echo(f"  Video clips: {clip_paths}")

    from karaokefx.sync import detect_bpm

    effective_bpm = bpm if bpm > 0 else detect_bpm(str(audio_path))
    if bpm > 0:
        click.echo(f"  BPM:       {effective_bpm:.1f} (forced)\n")
    else:
        click.echo(f"  BPM:       {effective_bpm:.1f} (auto-detected)\n")

    generate_video(
        audio_path=str(audio_path),
        bpm=effective_bpm,
        lyrics_path=str(lyrics_path),
        output_path=output,
        background=background,
        font_path=font,
        resolution=res,
        fps=fps,
        video_clip_paths=clip_paths,
        dim_opacity=dim_opacity,
    )

    click.echo(f"Done! Video saved to: {output}")


@cli.command()
@click.option("-a", "--audio", required=True, help="Audio file to transcribe")
@click.option("-o", "--output", default="output.lrc", help="Output LRC path")
@click.option("-m", "--model", default=config.DEFAULT_WHISPER_MODEL,
              type=click.Choice(config.WHISPER_MODELS), help="Whisper model size")
@click.option("-l", "--language", default=None, help="Language code (e.g. en, de)")
def transcribe(audio, output, model, language):
    """Transcribe audio to LRC (lyrics) file using Whisper."""
    click.echo(f"Loading Whisper model: {model}...")
    click.echo(f"Transcribing: {audio}")

    result = transcribe_audio(
        audio_path=audio,
        model_name=model,
        language=language,
    )

    result_to_lrc(result, output)
    click.echo(f"LRC saved to: {output}")


@cli.command()
@click.option("-a", "--audio", required=True, help="Audio file")
@click.option("-l", "--lyrics", required=True, help="Lyrics file (.lrc or .txt)")
def preview(audio, lyrics):
    """Preview lyrics sync timing in the terminal (quick check)."""
    import librosa

    lyrics_path = Path(lyrics)
    is_lrc = lyrics_path.suffix.lower() == ".lrc"

    # Get audio duration
    duration, sr = librosa.load(audio, sr=None, duration=None)
    total_ms = int(duration * 1000)

    if is_lrc:
        parsed = parse_lrc(str(lyrics_path))
    else:
        parsed = parse_plain_text(str(lyrics_path), total_duration_ms=total_ms)

    click.echo(f"\n--- Lyrics Preview ({len(parsed.lines)} lines) ---")
    for line in parsed.lines:
        start_sec = line.start_ms / 1000
        mins = int(start_sec // 60)
        secs = start_sec % 60
        print(f"  [{mins:02d}:{secs:05.2f}] {line.text}")

    click.echo(f"\nTotal duration: {duration:.1f}s")




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

    click.echo(f"\nDone! {successes} succeeded, {failures} failed.")

# Expose parse_timestamp for testing
__all__ = ["parse_timestamp"]
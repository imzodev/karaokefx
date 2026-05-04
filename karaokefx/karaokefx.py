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

    generate_video(
        audio_path=str(audio_path),
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
    import torch

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
    from tqdm import tqdm
    import librosa

    lyrics_path = Path(lyrics)
    is_lrc = lyrics_path.suffix.lower() == ".lrc"

    # Get audio duration
    duration, sr = librosa.load(audio, sr=None, duration=None)
    total_ms = int(duration * 1000)

    if is_lrc:
        parsed = parse_lrc(str(lyrics_path))
    else:
        parsed = parse_plain_text(str(lyrics_path), num_lines=None, total_duration_ms=total_ms)

    click.echo(f"\n--- Lyrics Preview ({len(parsed.lines)} lines) ---")
    for line in parsed.lines:
        start_sec = line.start_ms / 1000
        mins = int(start_sec // 60)
        secs = start_sec % 60
        print(f"  [{mins:02d}:{secs:05.2f}] {line.text}")

    click.echo(f"\nTotal duration: {duration:.1f}s")


# Expose parse_timestamp for testing
__all__ = ["parse_timestamp"]
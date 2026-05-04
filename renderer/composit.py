"""Main video composition pipeline — ties audio, lyrics, and background together."""

import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple
import tempfile

from moviepy import (
    CompositeVideoClip,
    VideoFileClip,
    AudioClip,
    ImageClip,
    concatenate_videoclips,
)
import numpy as np

from .text import draw_lyric_frame, draw_word_highlight
from .backgrounds import (
    generate_abstract_gradient,
    generate_particles,
    generate_geometric,
    generate_waveform,
)


# Map background type string to generator function
BG_GENERATORS = {
    "abstract-gradient": generate_abstract_gradient,
    "particles": generate_particles,
    "geometric": generate_geometric,
    "waveform": generate_waveform,
}


def generate_video(
    audio_path: str,
    lyrics_path: str,
    output_path: str,
    background: str = "abstract-gradient",
    font_path: Optional[str] = None,
    resolution: Tuple[int, int] = (1920, 1080),
    fps: int = 30,
) -> None:
    """Main entry point: compose audio + lyrics + background into a video.

    Args:
        audio_path: Path to audio file
        lyrics_path: Path to LRC or TXT lyrics file
        output_path: Where to save the output MP4
        background: Background type name
        font_path: Optional .ttf/.otf font path
        resolution: (width, height) tuple
        fps: frames per second
    """
    from ..sync import parse_lrc, parse_plain_text

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Parse lyrics
    lyrics_ext = Path(lyrics_path).suffix.lower()
    if lyrics_ext == ".lrc":
        lyrics = parse_lrc(lyrics_path)
    else:
        # Get audio duration via librosa
        import librosa
        duration, _ = librosa.load(audio_path, sr=None, duration=None)
        total_ms = int(duration * 1000)
        lyrics = parse_plain_text(lyrics_path, num_lines=None, total_duration_ms=total_ms)

    # Get audio duration
    import librosa
    duration, sr = librosa.load(audio_path, sr=None, duration=None)

    bg_gen = BG_GENERATORS.get(background, generate_abstract_gradient)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        frames_dir = tmpdir / "frames"
        frames_dir.mkdir()

        total_frames = int(duration * fps)

        print(f"Rendering {total_frames} frames...")
        for i in range(total_frames):
            t = i / fps

            # Find active lyric line
            t_ms = int(t * 1000)
            active_line = None
            prev_line = None

            for idx, line in enumerate(lyrics.lines):
                if line.start_ms <= t_ms < line.end_ms:
                    active_line = line
                    prev_line = lyrics.lines[idx - 1] if idx > 0 else None
                    break

            # Generate background
            bg = bg_gen(resolution, t)

            # Draw text on background
            if active_line:
                # Previous line (dimmed, top)
                if prev_line:
                    top_text = prev_line.text
                    top_img = draw_lyric_frame(
                        top_text, resolution, font_path=font_path,
                        font_size=52, text_color="#888888", position="center",
                    )
                    bg.paste(top_img, (0, 0), top_img)

                # Current line (highlighted, bottom)
                curr_img = draw_lyric_frame(
                    active_line.text, resolution, font_path=font_path,
                    font_size=72, text_color="#FFFFFF", highlight_color="#FFD700",
                    position="bottom",
                )
                bg.paste(curr_img, (0, 0), curr_img)

            frame_path = frames_dir / f"frame_{i:06d}.png"
            bg.save(frame_path, "PNG")

            if i % 300 == 0 and i > 0:
                print(f"  Frame {i}/{total_frames} done")

        print("Encoding video with FFmpeg...")

        # Build video from frames
        video_clip = VideoFileClip(str(frames_dir / "frame_000000.png")).with_duration(duration)
        video_clip = video_clip.with_fps(fps)

        # Encode frames as video first
        temp_video = tmpdir / "temp_video.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(frames_dir / "frame_%06d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-an",
            str(temp_video),
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        # Now mux audio
        cmd2 = [
            "ffmpeg", "-y",
            "-i", str(temp_video),
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(output_path),
        ]
        subprocess.run(cmd2, check=True, capture_output=True)

    print(f"Done! Saved to: {output_path}")
"""Main video composition pipeline — ties audio, lyrics, and background together."""

import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple
import tempfile

from PIL import Image
import numpy as np
from moviepy import (
    CompositeVideoClip,
    VideoFileClip,
    AudioClip,
    ImageClip,
    concatenate_videoclips,
)

from .text import draw_lyric_frame, draw_word_highlight
from .backgrounds import (
    generate_abstract_gradient,
    generate_particles,
    generate_geometric,
    generate_waveform,
    generate_video_loop,
    render_video_loop_clip,
)


# Map background type string to generator function
BG_GENERATORS = {
    "abstract-gradient": generate_abstract_gradient,
    "particles": generate_particles,
    "geometric": generate_geometric,
    "waveform": generate_waveform,
}


def _get_lyrics(audio_path: str, lyrics_path: str):
    """Parse lyrics file. Returns (Lyrics object, duration_seconds)."""
    from ..sync import parse_lrc, parse_plain_text
    import librosa

    lyrics_ext = Path(lyrics_path).suffix.lower()
    if lyrics_ext == ".lrc":
        lyrics = parse_lrc(lyrics_path)
    else:
        duration, _ = librosa.load(audio_path, sr=None, duration=None)
        total_ms = int(duration * 1000)
        lyrics = parse_plain_text(lyrics_path, num_lines=None, total_duration_ms=total_ms)

    duration, _ = librosa.load(audio_path, sr=None, duration=None)
    return lyrics, duration


def generate_video(
    audio_path: str,
    lyrics_path: str,
    output_path: str,
    background: str = "abstract-gradient",
    font_path: Optional[str] = None,
    resolution: Tuple[int, int] = (1920, 1080),
    fps: int = 30,
    video_loop_path: Optional[str] = None,
    dim_opacity: float = 0.4,
) -> None:
    """Main entry point: compose audio + lyrics + background into a video.

    Args:
        audio_path: Path to audio file
        lyrics_path: Path to LRC or TXT lyrics file
        output_path: Where to save the output MP4
        background: Background type name (abstract-gradient, particles, geometric, waveform)
        font_path: Optional .ttf/.otf font path
        resolution: (width, height) tuple
        fps: frames per second
        video_loop_path: Optional path to a video file to use as background (looped + dimmed)
        dim_opacity: When using video-loop, how much to dim the video (0.0 = none, 1.0 = full)
    """
    from ..sync import LyricLine

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lyrics, duration = _get_lyrics(audio_path, lyrics_path)

    # ── VIDEO-LOOP PATH ────────────────────────────────────────────────────────
    if background == "video-loop" and video_loop_path:
        _generate_with_video_loop(
            audio_path=audio_path,
            lyrics=lyrics,
            video_loop_path=video_loop_path,
            output_path=str(output_path),
            font_path=font_path,
            resolution=resolution,
            fps=fps,
            dim_opacity=dim_opacity,
            duration=duration,
        )
        print(f"Done! Saved to: {output_path}")
        return

    # ── GENERATIVE BACKGROUND PATH ────────────────────────────────────────────
    bg_gen = BG_GENERATORS.get(background, generate_abstract_gradient)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        frames_dir = tmpdir / "frames"
        frames_dir.mkdir()

        total_frames = int(duration * fps)

        print(f"Rendering {total_frames} frames ({background})...")
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
                if prev_line:
                    top_text = prev_line.text
                    top_img = draw_lyric_frame(
                        top_text, resolution, font_path=font_path,
                        font_size=52, text_color="#888888", position="center",
                    )
                    bg.paste(top_img, (0, 0), top_img)

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


def _generate_with_video_loop(
    audio_path: str,
    lyrics,
    video_loop_path: str,
    output_path: str,
    font_path: Optional[str],
    resolution: Tuple[int, int],
    fps: int,
    dim_opacity: float,
    duration: float,
) -> None:
    """Handle the video-loop + lyrics path.

    Uses the video as the background, dims it, then composites lyrics on top.
    """
    import cv2
    from ..sync import LyricLine

    cap = cv2.VideoCapture(video_loop_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_loop_path}")
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    video_frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    video_duration = video_frame_count / video_fps if video_fps > 0 else 0
    cap.release()

    if video_duration <= 0:
        raise ValueError(f"Could not read video duration from: {video_loop_path}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        frames_dir = tmpdir / "frames"
        frames_dir.mkdir()

        total_frames = int(duration * fps)

        print(f"Rendering {total_frames} frames (video-loop + lyrics)...")
        for i in range(total_frames):
            t = i / fps

            # ── Video frame (looped) ────────────────────────────────────────────
            loop_time = t % video_duration
            frame_idx = int(loop_time * video_fps)

            cap = cv2.VideoCapture(video_loop_path)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, cv2_frame = cap.read()
            cap.release()

            if ret:
                frame_rgb = cv2.cvtColor(cv2_frame, cv2.COLOR_BGR2RGB)
                bg = Image.fromarray(frame_rgb).resize(resolution, Image.LANCZOS)
            else:
                bg = Image.new("RGB", resolution, (0, 0, 0))

            # ── Dim overlay ────────────────────────────────────────────────────
            if dim_opacity > 0:
                dim_layer = Image.new("RGBA", resolution, (0, 0, 0, int(255 * dim_opacity)))
                bg_rgba = bg.convert("RGBA")
                bg_rgba = Image.alpha_composite(bg_rgba, dim_layer)
                bg = bg_rgba.convert("RGB")

            # ── Lyrics overlay ─────────────────────────────────────────────────
            t_ms = int(t * 1000)
            active_line = None
            prev_line = None

            for idx, line in enumerate(lyrics.lines):
                if line.start_ms <= t_ms < line.end_ms:
                    active_line = line
                    prev_line = lyrics.lines[idx - 1] if idx > 0 else None
                    break

            if active_line:
                if prev_line:
                    top_img = draw_lyric_frame(
                        prev_line.text, resolution, font_path=font_path,
                        font_size=52, text_color="#AAAAAA", position="center",
                    )
                    bg.paste(top_img, (0, 0), top_img)

                curr_img = draw_lyric_frame(
                    active_line.text, resolution, font_path=font_path,
                    font_size=72, text_color="#FFFFFF", highlight_color="#FFD700",
                    position="bottom",
                )
                bg.paste(curr_img, (0, 0), curr_img)

            bg.save(frames_dir / f"frame_{i:06d}.png", "PNG")

            if i % 300 == 0 and i > 0:
                print(f"  Frame {i}/{total_frames}")

        print("Encoding video...")

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

    print(f"Video-loop render complete!")
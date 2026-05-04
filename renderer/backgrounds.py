"""Animated background generation for karaoke videos."""

import numpy as np
from PIL import Image, ImageDraw
from typing import Tuple, Optional
import random


def generate_abstract_gradient(
    frame_size: Tuple[int, int],
    time: float,
    colors: Optional[list] = None,
) -> Image.Image:
    """Generate a slow-moving abstract gradient background.

    Args:
        frame_size: (width, height)
        time: animation time in seconds
        colors: list of hex color strings

    Returns:
        PIL Image
    """
    if colors is None:
        colors = ["#1a1a2e", "#16213e", "#0f3460", "#e94560", "#533483"]

    w, h = frame_size
    img = Image.new("RGB", frame_size)
    draw = ImageDraw.Draw(img)

    # Build gradient between color bands
    num_bands = len(colors)
    t = (np.sin(time * 0.3) + 1) / 2  # 0..1 slowly

    for y in range(h):
        # Which band are we in?
        band = int((y / h) * num_bands) % num_bands
        next_band = (band + 1) % num_bands

        # Mix based on position within band
        band_fraction = ((y / h) * num_bands) % 1.0
        blend = (np.sin(time * 0.2 + band) + 1) / 2

        c1 = _hex_to_rgb(colors[band])
        c2 = _hex_to_rgb(colors[next_band])

        r = int(c1[0] * (1 - band_fraction) + c2[0] * band_fraction)
        g = int(c1[1] * (1 - band_fraction) + c2[1] * band_fraction)
        b = int(c1[2] * (1 - band_fraction) + c2[2] * band_fraction)

        # Apply horizontal wave
        wave = int(20 * np.sin(y * 0.02 + time * 0.5))
        draw.line([(wave, y), (w + wave, y)], fill=(r, g, b))

    return img


def generate_particles(
    frame_size: Tuple[int, int],
    time: float,
    num_particles: int = 80,
    color: str = "#FFD700",
    bg_color: str = "#0a0a1a",
) -> Image.Image:
    """Floating particles background.

    Args:
        frame_size: (width, height)
        time: animation time in seconds
        num_particles: number of particles
        color: particle color
        bg_color: background color

    Returns:
        PIL Image
    """
    w, h = frame_size
    img = Image.new("RGB", frame_size, _hex_to_rgb(bg_color))
    draw = ImageDraw.Draw(img)

    rng = np.random.RandomState(int(time * 10))

    for _ in range(num_particles):
        x = int((rng.rand() + time * 0.1) % 1.0 * w)
        y = int((rng.rand() + time * 0.05) % 1.0 * h)
        radius = int(rng.rand() * 3 + 1)
        alpha = int(rng.rand() * 155 + 100)

        draw.ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill=_hex_to_rgb(color) + (alpha,),
        )

    return img


def generate_geometric(
    frame_size: Tuple[int, int],
    time: float,
    bg_color: str = "#0d0d1a",
) -> Image.Image:
    """Rotating/pulsing geometric shapes background.

    Args:
        frame_size: (width, height)
        time: animation time in seconds
        bg_color: background color

    Returns:
        PIL Image
    """
    w, h = frame_size
    cx, cy = w // 2, h // 2
    img = Image.new("RGB", frame_size, _hex_to_rgb(bg_color))
    draw = ImageDraw.Draw(img)

    # Outer ring
    radius = int(min(w, h) * 0.35)
    t = time * 0.4

    for i in range(8):
        angle = t + i * (np.pi / 4)
        offset = int(30 * np.sin(time * 0.8 + i))
        px = int(cx + (radius + offset) * np.cos(angle))
        py = int(cy + (radius + offset) * np.sin(angle))
        size = 20 + int(15 * np.sin(time + i))

        color_tuple = _hex_to_rgb(["#e94560", "#533483", "#0f3460", "#FFD700", "#1a1a2e"][i % 5])

        # Diamond shape
        points = [
            (px, py - size),
            (px + size, py),
            (px, py + size),
            (px - size, py),
        ]
        draw.polygon(points, fill=color_tuple)

    # Center circle
    pulse_r = int(min(w, h) * 0.1 + 10 * np.sin(time * 1.2))
    draw.ellipse(
        [cx - pulse_r, cy - pulse_r, cx + pulse_r, cy + pulse_r],
        outline="#FFD700",
        width=3,
    )

    return img


def generate_waveform(
    frame_size: Tuple[int, int],
    time: float,
    audio_samples: Optional[np.ndarray] = None,
    color: str = "#00D4FF",
    bg_color: str = "#0a0a1a",
) -> Image.Image:
    """Audio waveform visualization as background.

    Args:
        frame_size: (width, height)
        time: animation time in seconds
        audio_samples: pre-computed waveform samples (optional, uses fake data if None)
        color: waveform color
        bg_color: background color

    Returns:
        PIL Image
    """
    w, h = frame_size
    img = Image.new("RGB", frame_size, _hex_to_rgb(bg_color))
    draw = ImageDraw.Draw(img)

    if audio_samples is None:
        # Fake waveform for preview purposes
        t = np.linspace(0, time * 4, w)
        amplitude = np.sin(t * 2) * 0.3 + np.sin(t * 5) * 0.15 + np.sin(t * 11) * 0.1
        samples = amplitude
    else:
        samples = audio_samples[:w]

    mid_y = h // 2
    max_amp = h // 3

    points = []
    for x in range(min(w, len(samples))):
        y = int(mid_y + samples[x] * max_amp)
        points.append((x, y))

    if len(points) > 1:
        draw.line(points, fill=_hex_to_rgb(color), width=2)

    return img


def render_background_video(
    background_type: str,
    frame_size: Tuple[int, int],
    duration: float,
    fps: int,
    output_path: str,
    **kwargs,
) -> None:
    """Render a full background video to disk.

    Args:
        background_type: BG_ABSTRACT_GRADIENT, BG_PARTICLES, etc.
        frame_size: (width, height)
        duration: total video duration in seconds
        fps: frames per second
        output_path: where to save the video
        **kwargs: extra args passed to background generator
    """
    import subprocess
    from pathlib import Path

    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    num_frames = int(duration * fps)
    frames_dir = output_dir / "._temp_frames"
    frames_dir.mkdir(exist_ok=True)

    generators = {
        "abstract-gradient": generate_abstract_gradient,
        "particles": generate_particles,
        "geometric": generate_geometric,
        "waveform": generate_waveform,
    }

    gen = generators.get(background_type, generate_abstract_gradient)

    for i in range(num_frames):
        t = i / fps
        frame = gen(frame_size, t, **kwargs)
        frame.save(frames_dir / f"frame_{i:06d}.png", "PNG")

    # Encode with FFmpeg
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(frames_dir / "frame_%06d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-an",  # no audio for background
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    # Cleanup temp frames
    import shutil
    shutil.rmtree(frames_dir)


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
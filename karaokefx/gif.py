"""GIF export utility for KaraokeFX."""

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

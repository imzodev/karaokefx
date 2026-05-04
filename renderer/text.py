"""Text overlay rendering for karaoke lyrics."""

from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
import numpy as np


# Default font path — try to find a decent system font
DEFAULT_FONT_PATHS = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def get_default_font(size: int = 72) -> ImageFont.FreeTypeFont:
    """Try to load a system font, fallback to default PIL font."""
    for path in DEFAULT_FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_lyric_frame(
    text: str,
    frame_size: Tuple[int, int],
    font_path: Optional[str] = None,
    font_size: int = 72,
    text_color: str = "#FFFFFF",
    highlight_color: str = "#FFD700",
    stroke_color: str = "#000000",
    stroke_width: int = 3,
    shadow_color: str = "#000000",
    shadow_offset: Tuple[int, int] = (4, 4),
    position: str = "center",
) -> Image.Image:
    """Draw a single karaoke lyric frame onto a PIL Image.

    Args:
        text: The lyric text to render
        frame_size: (width, height) of the output frame
        font_path: Path to .ttf/.otf font, or None for default
        font_size: Font size in pixels
        text_color: Main text fill color
        highlight_color: Active word color
        stroke_color: Text outline color
        stroke_width: Text outline width in pixels
        shadow_color: Drop shadow color
        shadow_offset: (x, y) shadow offset
        position: "center" or "bottom"

    Returns:
        PIL Image with rendered text
    """
    img = Image.new("RGBA", frame_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Load font
    if font_path:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = get_default_font(font_size)
    else:
        font = get_default_font(font_size)

    # Calculate position
    if position == "bottom":
        # Place text in lower third
        target_y = int(frame_size[1] * 0.75)
    else:
        # Center
        target_y = frame_size[1] // 2

    # Get text size for centering
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (frame_size[0] - text_w) // 2

    # Draw shadow
    for dx, dy in [(0, 1), (1, 0), (1, 1)]:
        draw.text(
            (text_x + dx * shadow_offset[0], target_y + dy * shadow_offset[1]),
            text,
            font=font,
            fill=(*_hex_to_rgb(shadow_color), 180),
        )

    # Draw stroke (outline)
    for angle in range(0, 360, 30):
        dx = int(round(stroke_width * np.cos(np.radians(angle))))
        dy = int(round(stroke_width * np.sin(np.radians(angle))))
        draw.text(
            (text_x + dx, target_y + dy),
            text,
            font=font,
            fill=stroke_color,
        )

    # Draw main text
    draw.text(
        (text_x, target_y),
        text,
        font=font,
        fill=_hex_to_rgb(text_color),
    )

    return img


def draw_word_highlight(
    words: list,
    current_word_idx: int,
    frame_size: Tuple[int, int],
    font_path: Optional[str] = None,
    font_size: int = 72,
    text_color: str = "#FFFFFF",
    highlight_color: str = "#FFD700",
    stroke_color: str = "#000000",
) -> Image.Image:
    """Draw a lyric frame with word-by-word highlighting.

    Args:
        words: List of dicts [{text, start_ms, end_ms}, ...]
        current_word_idx: Index of the currently active word
        frame_size: (width, height)
        font_path: Path to font file
        font_size: Font size
        text_color: Color for inactive words
        highlight_color: Color for active word
        stroke_color: Outline color

    Returns:
        PIL Image with word-level highlight
    """
    img = Image.new("RGBA", frame_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if font_path:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = get_default_font(font_size)
    else:
        font = get_default_font(font_size)

    # Compute total text width for centering
    full_text = " ".join(w["text"] for w in words)
    bbox = draw.textbbox((0, 0), full_text, font=font)
    total_w = bbox[2] - bbox[0]
    x_offset = (frame_size[0] - total_w) // 2
    y_offset = int(frame_size[1] * 0.75)

    current_x = x_offset
    for i, word in enumerate(words):
        color = highlight_color if i == current_word_idx else text_color

        # Stroke
        for angle in range(0, 360, 45):
            dx = int(round(2 * np.cos(np.radians(angle))))
            dy = int(round(2 * np.sin(np.radians(angle))))
            draw.text(
                (current_x + dx, y_offset + dy),
                word["text"],
                font=font,
                fill=stroke_color,
            )

        # Fill
        draw.text(
            (current_x, y_offset),
            word["text"],
            font=font,
            fill=_hex_to_rgb(color),
        )

        # Advance x
        word_bbox = draw.textbbox((0, 0), word["text"] + " ", font=font)
        word_w = word_bbox[2] - word_bbox[0]
        current_x += word_w

    return img


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
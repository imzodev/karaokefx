"""KaraokeFX configuration defaults and constants."""

from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Default fonts directory
FONTS_DIR = PROJECT_ROOT / "fonts"

# Resolution presets
RESOLUTION_PORTRAIT = (1080, 1920)
RESOLUTION_LANDSCAPE = (1920, 1080)
RESOLUTION_DEFAULT = RESOLUTION_LANDSCAPE

# Video defaults
DEFAULT_FPS = 30
DEFAULT_CODEC = "libx264"
DEFAULT_AUDIO_CODEC = "aac"

# Background types
BG_ABSTRACT_GRADIENT = "abstract-gradient"
BG_PARTICLES = "particles"
BG_GEOMETRIC = "geometric"
BG_WAVEFORM = "waveform"
BG_VIDEO_LOOP = "video-loop"

BG_VIDEO_LOOP = "video-loop"

BACKGROUND_TYPES = [
    BG_ABSTRACT_GRADIENT,
    BG_PARTICLES,
    BG_GEOMETRIC,
    BG_WAVEFORM,
    BG_VIDEO_LOOP,
]

# Whisper model sizes
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]
DEFAULT_WHISPER_MODEL = "small"

# Default font (bundled Bebas Neue)
DEFAULT_FONT = FONTS_DIR / "BebasNeue.ttf"

# Text defaults
DEFAULT_FONT_SIZE = 72
DEFAULT_TEXT_COLOR = "#FFFFFF"
DEFAULT_HIGHLIGHT_COLOR = "#FFD700"
DEFAULT_BG_PADDING = 40

# LRC timestamp regex
LRC_TIMESTAMP_RE = r'\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)'
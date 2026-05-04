"""Renderer subpackage for KaraokeFX."""

from .text import draw_lyric_frame, render_lyric_clip
from .backgrounds import (
    generate_abstract_gradient,
    generate_particles,
    generate_geometric,
    generate_waveform,
    render_background_video,
)
from .composit import generate_video

__all__ = [
    "draw_lyric_frame",
    "render_lyric_clip",
    "generate_abstract_gradient",
    "generate_particles",
    "generate_geometric",
    "generate_waveform",
    "render_background_video",
    "generate_video",
]
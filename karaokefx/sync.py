"""LRC and plain-text lyrics parsing and word-level sync utilities."""

import re
from dataclasses import dataclass, field
from typing import List, Optional

import librosa

from .config import LRC_TIMESTAMP_RE


# Color tag regex: [color:#RRGGBB]
LRC_COLOR_TAG_RE = re.compile(r'\[color:([0-9A-Fa-f]{6})\]')


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


@dataclass
class LyricLine:
    """A single lyric line with start/end timestamps and optional word-level timing."""
    start_ms: int
    end_ms: int
    text: str
    words: List[dict] = field(default_factory=list)
    text_color: str = "#FFFFFF"
    highlight_color: str = "#FFD700"

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


@dataclass
class Lyrics:
    """Parsed lyrics container."""
    lines: List[LyricLine]
    source_format: str  # "lrc" or "plain"


def parse_lrc(lrc_path: str, audio_duration_ms: Optional[int] = None) -> Lyrics:
    """Parse an LRC file into Lyrics object.

    Supports:
      [mm:ss.xx] lyric line            — line-level timestamps
      [mm:ss.xx] <mm:ss.xx>word ...   — word-level timestamps
      [color:#RRGGBB]                  — color tag for subsequent lines
    """
    lines: List[LyricLine] = []
    pattern = re.compile(LRC_TIMESTAMP_RE)

    with open(lrc_path, "r", encoding="utf-8") as f:
        active_text_color = "#FFFFFF"
        active_highlight = "#FFD700"

        for raw in f:
            raw = raw.strip()
            if not raw:
                continue

            # Color tag — update active colors for subsequent lines
            color_m = LRC_COLOR_TAG_RE.match(raw)
            if color_m:
                hex_color = "#" + color_m.group(1)
                active_text_color = hex_color
                active_highlight = hex_color
                continue

            # Check for word-level timing: [00:12.00]<00:12.00>word<00:12.50>word
            word_line = _parse_word_level_line(raw, pattern)
            if word_line is not None:
                word_line.text_color = active_text_color
                word_line.highlight_color = active_highlight
                lines.append(word_line)
                continue

            # Line-level timing
            m = pattern.match(raw)
            if m:
                minutes = int(m.group(1))
                seconds = float(f"{m.group(2)}.{m.group(3)}")
                start_ms = int((minutes * 60 + seconds) * 1000)
                text = m.group(4).strip()

                lines.append(LyricLine(
                    start_ms=start_ms,
                    end_ms=start_ms,  # filled in post-processing
                    text=text,
                    text_color=active_text_color,
                    highlight_color=active_highlight,
                ))

    # Post-process: fill end_ms from next line's start
    for i in range(len(lines) - 1):
        if lines[i].end_ms == lines[i].start_ms:
            lines[i] = LyricLine(
                start_ms=lines[i].start_ms,
                end_ms=lines[i + 1].start_ms,
                text=lines[i].text,
                words=lines[i].words,
                text_color=lines[i].text_color,
                highlight_color=lines[i].highlight_color,
            )

    # Last line: use actual audio duration if provided, else +30s fallback
    if lines:
        final_end = audio_duration_ms if audio_duration_ms else lines[-1].start_ms + 30_000
        lines[-1] = LyricLine(
            start_ms=lines[-1].start_ms,
            end_ms=final_end,
            text=lines[-1].text,
            words=lines[-1].words,
            text_color=lines[-1].text_color,
            highlight_color=lines[-1].highlight_color,
        )

    return Lyrics(lines=lines, source_format="lrc")


def _parse_word_level_line(raw: str, pattern: re.Pattern) -> Optional[LyricLine]:
    """Parse a line with embedded word-level timestamps like:
    [00:12.00]<00:12.00>Hello <00:12.50>World

    Returns LyricLine or None if no word-level timing found.
    """
    m = pattern.match(raw)
    if not m or "<" not in raw:
        return None

    minutes = int(m.group(1))
    seconds = float(f"{m.group(2)}.{m.group(3)}")
    start_ms = int((minutes * 60 + seconds) * 1000)
    text_part = m.group(4)

    word_pattern = re.compile(r'<(\d{2}):(\d{2})\.(\d{2,3})>([^<\[]+)')
    words = []
    for wm in word_pattern.finditer(text_part):
        w_min = int(wm.group(1))
        w_sec = float(f"{wm.group(2)}.{wm.group(3)}")
        w_ms = int((w_min * 60 + w_sec) * 1000)
        w_text = wm.group(4).strip()
        words.append({"text": w_text, "start_ms": w_ms, "end_ms": w_ms})

    # Fill end_ms between consecutive words
    for i in range(len(words) - 1):
        words[i]["end_ms"] = words[i + 1]["start_ms"]

    end_ms = words[-1]["end_ms"] + 5000 if words else start_ms + 5000

    return LyricLine(start_ms=start_ms, end_ms=end_ms, text=text_part, words=words)


def parse_plain_text(txt_path: str, total_duration_ms: int, bpm: float = 0.0) -> Lyrics:
    """Parse a plain-text lyrics file, distributing lines across the song duration.

    Args:
        txt_path: path to .txt file
        total_duration_ms: total audio duration in milliseconds
        bpm: optional BPM for beat-synchronized distribution (0 = uniform spacing)
    """
    with open(txt_path, "r", encoding="utf-8") as f:
        raw_lines = [ln.strip() for ln in f if ln.strip()]

    if not raw_lines:
        return Lyrics(lines=[], source_format="plain")

    if bpm > 0:
        # Beat-synchronized distribution
        ms_per_beat = bpm_to_ms_per_beat(bpm)
        lines = []
        for i, text in enumerate(raw_lines):
            start_ms = int(i * ms_per_beat)
            end_ms = int((i + 1) * ms_per_beat) if i < len(raw_lines) - 1 else total_duration_ms
            lines.append(LyricLine(start_ms=start_ms, end_ms=end_ms, text=text))
    else:
        # Uniform distribution
        interval = total_duration_ms / len(raw_lines)
        lines = []
        for i, text in enumerate(raw_lines):
            start_ms = int(i * interval)
            end_ms = int((i + 1) * interval) if i < len(raw_lines) - 1 else total_duration_ms
            lines.append(LyricLine(start_ms=start_ms, end_ms=end_ms, text=text))

    return Lyrics(lines=lines, source_format="plain")
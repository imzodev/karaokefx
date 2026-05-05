"""LRC and plain-text lyrics parsing and word-level sync utilities."""

import re
from dataclasses import dataclass
from typing import List, Optional

from .config import LRC_TIMESTAMP_RE


@dataclass
class LyricLine:
    """A single lyric line with start/end timestamps and optional word-level timing."""
    start_ms: int       # Start time in milliseconds
    end_ms: int         # End time in milliseconds
    text: str           # Full line text
    words: List[dict] = []  # [{text, start_ms, end_ms}, ...] or empty

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
      [mm:ss.xx] <mm:ss.xx>word ...   — word-level timestamps (Karat time format)
    """
    lines: List[LyricLine] = []
    pattern = re.compile(LRC_TIMESTAMP_RE)

    with open(lrc_path, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue

            # Check for word-level timing: [00:12.00]<00:12.00>word<00:12.50>word
            word_level = parse_word_level(raw, pattern)
            if word_level is not None:
                lines.append(word_level)
                continue

            # Line-level timing
            m = pattern.match(raw)
            if m:
                minutes = int(m.group(1))
                seconds = float(f"{m.group(2)}.{m.group(3)}")
                start_ms = int((minutes * 60 + seconds) * 1000)
                text = m.group(4).strip()

                # Use next line's start as our end_ms (filled in post-processing)
                lines.append(LycLine(start_ms=start_ms, end_ms=start_ms, text=text))

    # Post-process: fill end_ms from next line's start
    for i in range(len(lines) - 1):
        if lines[i].end_ms == lines[i].start_ms:
            lines[i] = LyricLine(
                start_ms=lines[i].start_ms,
                end_ms=lines[i + 1].start_ms,
                text=lines[i].text,
                words=lines[i].words,
            )

    # Last line gets end_ms from audio duration if provided, else fallback
    if lines:
        final_end = audio_duration_ms if audio_duration_ms else lines[-1].start_ms + 30_000
        lines[-1] = LyricLine(
            start_ms=lines[-1].start_ms,
            end_ms=final_end,
            text=lines[-1].text,
            words=lines[-1].words,
        )

    return Lyrics(lines=lines, source_format="lrc")


def parse_word_level(raw: str, pattern: re.Pattern) -> Optional[LyricLine]:
    """Parse word-level timestamped line like:
    [00:12.00]<00:12.00>Hello <00:12.50>World
    Returns LyricLine or None.
    """
    m = pattern.match(raw)
    if not m:
        return None

    # Check if there are embedded word timestamps
    if "<" not in raw:
        return None

    minutes = int(m.group(1))
    seconds = float(f"{m.group(2)}.{m.group(3)}")
    start_ms = int((minutes * 60 + seconds) * 1000)
    text_part = m.group(4)

    # Parse word timings: <mm:ss.xx>word
    word_pattern = re.compile(r'<(\d{2}):(\d{2})\.(\d{2,3})>([^<\[]+)')
    words = []
    for wm in word_pattern.finditer(text_part):
        w_min = int(wm.group(1))
        w_sec = float(f"{wm.group(2)}.{wm.group(3)}")
        w_ms = int((w_min * 60 + w_sec) * 1000)
        w_text = wm.group(4).strip()
        words.append({"text": w_text, "start_ms": w_ms, "end_ms": w_ms})  # end filled later

    # Fill end_ms for words
    for i in range(len(words) - 1):
        words[i]["end_ms"] = words[i + 1]["start_ms"]

    end_ms = words[-1]["end_ms"] + 5000 if words else start_ms + 5000

    return LyricLine(start_ms=start_ms, end_ms=end_ms, text=text_part, words=words)


def parse_plain_text(txt_path: str, total_duration_ms: int) -> Lyrics:
    """Parse plain text file, distributing lines evenly across duration.

    Args:
        txt_path: path to .txt file
        num_lines: number of lyric lines (derived from file)
        total_duration_ms: total audio duration in milliseconds
    """
    with open(txt_path, "r", encoding="utf-8") as f:
        raw_lines = [ln.strip() for ln in f if ln.strip()]

    if not raw_lines:
        return Lyrics(lines=[], source_format="plain")

    interval = total_duration_ms / len(raw_lines)
    lines = []
    for i, text in enumerate(raw_lines):
        start_ms = int(i * interval)
        end_ms = int((i + 1) * interval) if i < len(raw_lines) - 1 else total_duration_ms
        lines.append(LyricLine(start_ms=start_ms, end_ms=end_ms, text=text))

    return Lyrics(lines=lines, source_format="plain")
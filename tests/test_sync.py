"""Tests for KaraokeFX sync module."""

import pytest
import tempfile
import os
from karaokefx.sync import parse_lrc, parse_plain_text, LyricLine


def test_parse_lrc_basic():
    """Test basic LRC parsing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".lrc", delete=False) as f:
        f.write("[00:12.50] Hello world\n")
        f.write("[00:17.80] This is a test\n")
        f.write("[00:25.00] Third line\n")
        temp_path = f.name

    try:
        lyrics = parse_lrc(temp_path)
        assert len(lyrics.lines) == 3
        assert lyrics.lines[0].text == "Hello world"
        assert lyrics.lines[0].start_ms == 12500
        assert lyrics.lines[1].start_ms == 17800
        assert lyrics.source_format == "lrc"
    finally:
        os.unlink(temp_path)


def test_parse_lrc_ms_precision():
    """Test millisecond precision in LRC timestamps."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".lrc", delete=False) as f:
        f.write("[00:01.23] One\n")
        f.write("[00:04.56] Two\n")
        temp_path = f.name

    try:
        lyrics = parse_lrc(temp_path)
        assert lyrics.lines[0].start_ms == 1230
        assert lyrics.lines[1].start_ms == 4560
    finally:
        os.unlink(temp_path)


def test_parse_plain_text():
    """Test plain text lyrics are evenly distributed."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Line one\n")
        f.write("Line two\n")
        f.write("Line three\n")
        temp_path = f.name

    try:
        lyrics = parse_plain_text(temp_path, num_lines=3, total_duration_ms=30000)
        assert len(lyrics.lines) == 3
        assert lyrics.lines[0].text == "Line one"
        assert lyrics.lines[0].start_ms == 0
        assert lyrics.lines[-1].end_ms == 30000
        assert lyrics.source_format == "plain"
    finally:
        os.unlink(temp_path)


def test_parse_lrc_empty_lines_skipped():
    """Test that blank lines in LRC are skipped."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".lrc", delete=False) as f:
        f.write("[00:10.00] First\n")
        f.write("\n")
        f.write("[00:15.00] Second\n")
        temp_path = f.name

    try:
        lyrics = parse_lrc(temp_path)
        assert len(lyrics.lines) == 2
        assert lyrics.lines[1].text == "Second"
    finally:
        os.unlink(temp_path)


def test_lyric_line_dataclass():
    """Test LyricLine dataclass properties."""
    line = LyricLine(start_ms=5000, end_ms=10000, text="Test line", words=[])
    assert line.duration_ms == 5000
    assert line.start_ms == 5000
    assert line.end_ms == 10000
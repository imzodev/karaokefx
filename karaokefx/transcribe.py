"""Whisper transcription integration."""

import whisper
from pathlib import Path
from typing import Optional

from .config import DEFAULT_WHISPER_MODEL


def load_model(model_name: str = DEFAULT_WHISPER_MODEL) -> whisper.Whisper:
    """Load and return a Whisper model.

    Args:
        model_name: whisper model size (tiny, base, small, medium, large)

    Returns:
        Loaded Whisper model
    """
    model = whisper.load_model(model_name)
    return model


def transcribe_audio(
    audio_path: str,
    model_name: str = DEFAULT_WHISPER_MODEL,
    language: Optional[str] = None,
    task: str = "transcribe",
) -> whisper.utils.Result:
    """Transcribe an audio file to text with word-level timestamps.

    Args:
        audio_path: path to audio file (mp3, wav, m4a, flac, etc.)
        model_name: whisper model size
        language: force language (None = auto-detect)
        task: "transcribe" or "translate"

    Returns:
        Whisper result dict with segments -> words
    """
    model = load_model(model_name)

    options = dict(
        language=language,
        task=task,
        word_timestamps=True,
    )

    result = model.transcribe(audio_path, **options)
    return result


def result_to_lrc(result: dict, output_path: str) -> None:
    """Convert Whisper result to LRC file with word-level timestamps.

    Args:
        result: Whisper result dict
        output_path: path to write .lrc file
    """
    with open(output_path, "w", encoding="utf-8") as f:
        for segment in result.get("segments", []):
            start = segment["start"]
            text = segment["text"].strip()

            # Line-level LRC entry
            mins = int(start // 60)
            secs = start % 60
            timestamp = f"[{mins:02d}:{secs:05.2f}]"
            f.write(f"{timestamp}{text}\n")

            # Word-level entries on next lines
            for word in segment.get("words", []):
                w_start = word["start"]
                w_mins = int(w_start // 60)
                w_secs = w_start % 60
                w_text = word["word"].strip()
                f.write(f"  <{w_mins:02d}:{w_secs:05.2f}>{w_text}\n")
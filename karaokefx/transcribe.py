"""Whisper transcription integration."""

import sys
sys.stderr.write("[transcribe.py] MODULE LOADING\n")
sys.stderr.flush()

import whisper
from pathlib import Path
from typing import Optional

from .config import DEFAULT_WHISPER_MODEL

sys.stderr.write(f"[transcribe.py] DEFAULT_WHISPER_MODEL = {DEFAULT_WHISPER_MODEL}\n")
sys.stderr.flush()


def load_model(model_name: str = DEFAULT_WHISPER_MODEL) -> whisper.Whisper:
    """Load and return a Whisper model.

    Downloads the model if not already cached. This may take a few minutes
    for larger models (medium, large).

    Args:
        model_name: whisper model size (tiny, base, small, medium, large)

    Returns:
        Loaded Whisper model
    """
    sys.stderr.write(f"[Whisper] Downloading/loading model '{model_name}'...\n")
    sys.stderr.flush()
    try:
        model = whisper.load_model(model_name)
        sys.stderr.write(f"[Whisper] Model loaded successfully.\n")
        sys.stderr.flush()
        return model
    except Exception as e:
        sys.stderr.write(f"[Whisper] ERROR loading model: {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()
        raise


def transcribe_audio(
    audio_path: str,
    model_name: str = DEFAULT_WHISPER_MODEL,
    language: Optional[str] = None,
    task: str = "transcribe",
) -> dict:
    """Transcribe an audio file to text with word-level timestamps.

    Args:
        audio_path: path to audio file (mp3, wav, m4a, flac, etc.)
        model_name: whisper model size
        language: force language (None = auto-detect)
        task: "transcribe" or "translate"

    Returns:
        Whisper result dict with segments -> words
    """
    sys.stderr.write(f"[transcribe_audio] called with audio_path={audio_path}, model_name={model_name}, language={language}\n")
    sys.stderr.flush()

    model = load_model(model_name)

    options = dict(
        language=language,
        task=task,
        word_timestamps=True,
    )

    language_note = f" language '{language}'" if language else " (auto-detect)"
    sys.stderr.write(f"[Whisper] Transcribing {audio_path}{language_note}...\n")
    sys.stderr.flush()

    try:
        result = model.transcribe(audio_path, **options)
        sys.stderr.write(f"[Whisper] Transcription complete. text length: {len(result.get('text',''))}, segments: {len(result.get('segments',[]))}\n")
        sys.stderr.flush()
        return result
    except Exception as e:
        sys.stderr.write(f"[Whisper] Transcription ERROR: {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()
        raise


def result_to_lrc(result: dict, output_path: str) -> None:
    """Convert Whisper result to LRC file with word-level timestamps.

    Args:
        result: Whisper result dict
        output_path: path to write .lrc file
    """
    sys.stderr.write(f"[result_to_lrc] called with output_path={output_path}\n")
    sys.stderr.flush()

    lines_written = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for segment in result.get("segments", []):
            start = segment["start"]
            text = segment["text"].strip()

            mins = int(start // 60)
            secs = start % 60
            timestamp = f"[{mins:02d}:{secs:05.2f}]"
            f.write(f"{timestamp}{text}\n")
            lines_written += 1

            for word in segment.get("words", []):
                w_start = word["start"]
                w_mins = int(w_start // 60)
                w_secs = w_start % 60
                w_text = word["word"].strip()
                f.write(f"  <{w_mins:02d}:{w_secs:05.2f}>{w_text}\n")

    sys.stderr.write(f"[result_to_lrc] Done — {lines_written} lyric lines written to {output_path}\n")
    sys.stderr.flush()
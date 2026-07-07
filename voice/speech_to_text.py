from __future__ import annotations

import os
import sys
import time
from typing import Any


class SpeechToText:
    _model = None

    @classmethod
    def get_model(cls) -> Any:
        if cls._model is None:
            print("[STT] Initializing faster-whisper model ('small') on CPU...", file=sys.stderr)
            start_time = time.time()
            from faster_whisper import WhisperModel
            
            # Using CPU and float32 for maximum compatibility on Render and local dev
            cls._model = WhisperModel("small", device="cpu", compute_type="float32")
            print(f"[STT] Whisper model loaded in {time.time() - start_time:.2f} seconds.", file=sys.stderr)
        return cls._model

    @classmethod
    def transcribe(cls, file_path: str) -> str:
        model = cls.get_model()
        print(f"[STT] Transcribing file: {file_path}", file=sys.stderr)
        start_time = time.time()
        
        segments, info = model.transcribe(file_path, beam_size=5)
        text_segments = []
        for segment in segments:
            text_segments.append(segment.text)
            
        transcription = "".join(text_segments).strip()
        print(f"[STT] Transcription complete in {time.time() - start_time:.2f}s. Result: {transcription!r}", file=sys.stderr)
        return transcription


def initialize_whisper() -> None:
    """Pre-loads the Whisper model into memory at application startup."""
    try:
        SpeechToText.get_model()
    except Exception as exc:
        print(f"[STT] Error during Whisper pre-load: {exc}", file=sys.stderr)

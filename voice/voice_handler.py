from __future__ import annotations

import os
import sys
import tempfile
from typing import Any

from voice.audio_converter import AudioConverter
from voice.speech_to_text import SpeechToText
from voice.text_to_speech import TextToSpeech


class VoiceHandler:
    @classmethod
    def handle_incoming_voice(cls, audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
        """
        Saves incoming audio bytes to a temp file, converts to WAV,
        and transcribes it locally using faster-whisper.
        """
        print(f"[VoiceHandler] Processing incoming voice message, mime_type={mime_type}, bytes={len(audio_bytes)}", file=sys.stderr)
        
        # Determine suffix based on mime type
        suffix = ".ogg"
        if "aac" in mime_type:
            suffix = ".aac"
        elif "mp4" in mime_type or "m4a" in mime_type:
            suffix = ".m4a"

        # Create temporary files
        temp_dir = tempfile.gettempdir()
        incoming_path = os.path.join(temp_dir, f"incoming_{os.urandom(8).hex()}{suffix}")
        wav_path = os.path.join(temp_dir, f"transcribe_{os.urandom(8).hex()}.wav")

        try:
            # Step 1: Write raw bytes to disk
            with open(incoming_path, "wb") as f:
                f.write(audio_bytes)

            # Step 2: Convert to 16kHz WAV
            if not AudioConverter.convert_to_wav(incoming_path, wav_path):
                print("[VoiceHandler] Audio conversion to WAV failed.", file=sys.stderr)
                return ""

            # Step 3: Transcribe WAV
            transcription = SpeechToText.transcribe(wav_path)
            return transcription

        except Exception as exc:
            print(f"[VoiceHandler] Error during incoming voice handling: {exc}", file=sys.stderr)
            return ""

        finally:
            # Step 4: Cleanup temp files
            for p in (incoming_path, wav_path):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                        print(f"[VoiceHandler] Cleaned up temp file: {p}", file=sys.stderr)
                    except Exception as e:
                        print(f"[VoiceHandler] Failed to remove temp file {p}: {e}", file=sys.stderr)

    @classmethod
    async def handle_outgoing_voice(cls, text: str, language: str) -> bytes | None:
        """
        Synthesizes outgoing response text into speech using edge-tts,
        converts the resulting MP3 to OGG/Opus, and returns the OGG bytes.
        """
        print(f"[VoiceHandler] Synthesizing outgoing voice message, language={language}, text_len={len(text)}", file=sys.stderr)
        
        temp_dir = tempfile.gettempdir()
        mp3_path = os.path.join(temp_dir, f"reply_{os.urandom(8).hex()}.mp3")
        ogg_path = os.path.join(temp_dir, f"reply_{os.urandom(8).hex()}.ogg")

        try:
            # Step 1: Generate speech to MP3
            success = await TextToSpeech.generate_speech(text, language, mp3_path)
            if not success:
                print("[VoiceHandler] TextToSpeech generation failed.", file=sys.stderr)
                return None

            # Step 2: Convert MP3 to OGG/Opus
            success = AudioConverter.mp3_to_ogg(mp3_path, ogg_path)
            if not success:
                print("[VoiceHandler] Audio conversion to OGG failed.", file=sys.stderr)
                return None

            # Step 3: Read OGG bytes
            with open(ogg_path, "rb") as f:
                ogg_bytes = f.read()

            return ogg_bytes

        except Exception as exc:
            print(f"[VoiceHandler] Error during outgoing voice handling: {exc}", file=sys.stderr)
            return None

        finally:
            # Step 4: Cleanup temp files
            for p in (mp3_path, ogg_path):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                        print(f"[VoiceHandler] Cleaned up temp file: {p}", file=sys.stderr)
                    except Exception as e:
                        print(f"[VoiceHandler] Failed to remove temp file {p}: {e}", file=sys.stderr)

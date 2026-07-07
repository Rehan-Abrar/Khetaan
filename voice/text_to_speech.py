from __future__ import annotations

import asyncio
import sys
import edge_tts

URDU_VOICE = "ur-PK-UzmaNeural"
ENGLISH_VOICE = "en-US-AriaNeural"


async def _roman_urdu_reply_to_urdu_script(text: str) -> str:
    try:
        from utils.gemini_client import GeminiClient
        client = GeminiClient()
        prompt = (
            "You are a Nastaliq/Urdu script conversion assistant. "
            "Convert this Roman Urdu assistant reply (Urdu written in Latin/English alphabet) "
            "into proper Urdu script (Arabic letters) so that a text-to-speech engine can read it out loud. "
            "Do NOT translate it to English. Keep the words, meaning, and numbers exactly the same, but write them in Urdu script. "
            "Return ONLY the plain Urdu script text. Do not include JSON, code block formatting, or any explanations.\n\n"
            f"Roman Urdu Text:\n{text}"
        )
        response = await asyncio.to_thread(
            client.client.models.generate_content,
            model=client.model_name,
            contents=[prompt]
        )
        translated = (getattr(response, "text", "") or "").strip()
        if translated:
            return translated
        return text
    except Exception as exc:
        print(f"[TTS] Roman Urdu script conversion failed: {exc}", file=sys.stderr)
        return text


class TextToSpeech:
    @classmethod
    async def generate_speech(cls, text: str, language: str, output_path: str) -> bool:
        print(f"[TTS] Generating speech for language={language}. Input length={len(text)}", file=sys.stderr)
        try:
            voice = ENGLISH_VOICE
            text_to_speak = text

            if language == "roman_urdu":
                print("[TTS] Normalizing Roman Urdu to Urdu script via Gemini...", file=sys.stderr)
                text_to_speak = await _roman_urdu_reply_to_urdu_script(text)
                voice = URDU_VOICE
                print(f"[TTS] Normalized text: {text_to_speak!r}", file=sys.stderr)
            elif language == "urdu":
                voice = URDU_VOICE

            communicate = edge_tts.Communicate(text_to_speak, voice)
            await communicate.save(output_path)
            print(f"[TTS] Speech successfully saved to {output_path}", file=sys.stderr)
            return True
        except Exception as exc:
            print(f"[TTS] Error during speech generation: {exc}", file=sys.stderr)
            return False

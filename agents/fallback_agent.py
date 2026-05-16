from __future__ import annotations

import asyncio

from agents.prompts import FALLBACK_PROMPT
from utils.gemini_client import GeminiClient


class FallbackAgent:
    def __init__(self, model_name: str | None = None) -> None:
        try:
            self.client = GeminiClient(model_name=model_name)
        except RuntimeError:
            self.client = None

    async def respond(self, message: str, language: str = "roman_urdu") -> dict:
        message = message or ""
        if not self.client:
            return {
                "agent": "fallback_agent",
                "confidence": 50,
                "urdu_message": self._fallback_message(language),
            }

        parts = [
            FALLBACK_PROMPT,
            f"User message: {message}",
            self._language_instruction(language),
            "Return JSON only without code fences.",
        ]
        result = await asyncio.to_thread(self.client.generate_json, parts)
        if not isinstance(result, dict):
            return {
                "agent": "fallback_agent",
                "confidence": 50,
                "urdu_message": self._fallback_message(language),
            }

        result.setdefault("agent", "fallback_agent")
        result.setdefault("confidence", 50)
        result.setdefault("urdu_message", self._fallback_message(language))
        return result

    @staticmethod
    def _fallback_message(language: str) -> str:
        if language == "english":
            return "Sorry, I could not understand. You can ask about crop disease, weather, irrigation, or mandi rates."
        return "Maaf kijiye, sawal wazeh nahi. Aap fasal ki bimari, mausam, aabpashi ya mandi rate ke bare mein pooch sakte hain."

    @staticmethod
    def _language_instruction(language: str) -> str:
        if language == "english":
            return "Reply in English."
        return "Reply in Roman Urdu using Latin letters only. Do not use Urdu script."

from __future__ import annotations

import asyncio

from agents.prompts import HELP_AGENT_PROMPT
from utils.gemini_client import GeminiClient


class HelpAgent:
    def __init__(self, model_name: str | None = None) -> None:
        try:
            self.client = GeminiClient(model_name=model_name)
        except RuntimeError:
            self.client = None

    async def respond(self, language: str = "roman_urdu") -> dict:
        if not self.client:
            return {
                "agent": "help_agent",
                "urdu_message": self._help_message(language),
            }

        parts = [
            HELP_AGENT_PROMPT,
            self._language_instruction(language),
            "Return JSON only without code fences.",
        ]
        result = await asyncio.to_thread(self.client.generate_json, parts)
        if not isinstance(result, dict):
            return {
                "agent": "help_agent",
                "urdu_message": self._help_message(language),
            }

        result.setdefault("agent", "help_agent")
        result.setdefault("urdu_message", self._help_message(language))
        return result

    @staticmethod
    def _help_message(language: str) -> str:
        if language == "english":
            return "You can ask about crop disease, weather, irrigation, and mandi rates."
        return "Aap fasal ki bimari, mausam, aabpashi aur mandi rate ke bare mein pooch sakte hain."

    @staticmethod
    def _language_instruction(language: str) -> str:
        if language == "english":
            return "Reply in English."
        return "Reply in Roman Urdu using Latin letters only. Do not use Urdu script."

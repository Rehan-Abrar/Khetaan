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

    async def respond(self) -> dict:
        if not self.client:
            return {
                "agent": "help_agent",
                "urdu_message": "آپ فصل بیماری، موسم، آبپاشی اور منڈی ریٹ سے متعلق سوال کر سکتے ہیں۔",
            }

        parts = [
            HELP_AGENT_PROMPT,
            "Return JSON only without code fences.",
        ]
        result = await asyncio.to_thread(self.client.generate_json, parts)
        if not isinstance(result, dict):
            return {
                "agent": "help_agent",
                "urdu_message": "آپ فصل بیماری، موسم، آبپاشی اور منڈی ریٹ سے متعلق سوال کر سکتے ہیں۔",
            }

        result.setdefault("agent", "help_agent")
        result.setdefault("urdu_message", "آپ فصل بیماری، موسم، آبپاشی اور منڈی ریٹ سے متعلق سوال کر سکتے ہیں۔")
        return result

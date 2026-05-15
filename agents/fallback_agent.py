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

    async def respond(self, message: str) -> dict:
        message = message or ""
        if not self.client:
            return {
                "agent": "fallback_agent",
                "confidence": 50,
                "urdu_message": "معاف کیجئے، سوال واضح نہیں ہے۔ آپ فصل بیماری، موسم، آبپاشی یا منڈی ریٹ کے بارے میں پوچھ سکتے ہیں۔",
            }

        parts = [
            FALLBACK_PROMPT,
            f"User message: {message}",
            "Return JSON only without code fences.",
        ]
        result = await asyncio.to_thread(self.client.generate_json, parts)
        if not isinstance(result, dict):
            return {
                "agent": "fallback_agent",
                "confidence": 50,
                "urdu_message": "معاف کیجئے، سوال واضح نہیں ہے۔ آپ فصل بیماری، موسم، آبپاشی یا منڈی ریٹ کے بارے میں پوچھ سکتے ہیں۔",
            }

        result.setdefault("agent", "fallback_agent")
        result.setdefault("confidence", 50)
        result.setdefault(
            "urdu_message",
            "معاف کیجئے، سوال واضح نہیں ہے۔ آپ فصل بیماری، موسم، آبپاشی یا منڈی ریٹ کے بارے میں پوچھ سکتے ہیں۔",
        )
        return result

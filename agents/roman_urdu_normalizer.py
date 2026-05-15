from __future__ import annotations

import asyncio
from typing import Any

from agents.prompts import ROMAN_URDU_NORMALIZER_PROMPT
from utils.gemini_client import GeminiClient


class RomanUrduNormalizer:
    def __init__(self, model_name: str | None = None) -> None:
        try:
            self.client = GeminiClient(model_name=model_name)
        except RuntimeError:
            self.client = None

    async def normalize(self, message: str) -> dict[str, Any]:
        message = message or ""
        if not message or not self.client:
            return {"original": message, "urdu": message}

        parts = [
            ROMAN_URDU_NORMALIZER_PROMPT,
            f"Original: {message}",
            "Return JSON only without code fences.",
        ]
        result = await asyncio.to_thread(self.client.generate_json, parts)
        if not isinstance(result, dict):
            return {"original": message, "urdu": message}

        urdu = result.get("urdu") or message
        return {"original": message, "urdu": urdu}

from __future__ import annotations

import asyncio

from agents.prompts import DISEASE_AGENT_PROMPT
from utils.gemini_client import GeminiClient


class CropAgent:
    def __init__(self, model_name: str | None = None) -> None:
        try:
            self.client = GeminiClient(model_name=model_name)
        except RuntimeError:
            self.client = None

    async def diagnose(
        self,
        message: str | None,
        image_bytes: bytes | None,
        mime_type: str | None = None,
    ) -> dict:
        if not image_bytes:
            return {
                "agent": "disease_agent",
                "disease": "",
                "confidence": 0,
                "urgency": "low",
                "urdu_message": "براہ کرم فصل کی واضح تصویر بھیجیں تاکہ تشخیص ہو سکے۔",
                "suggestions": [],
            }

        if not self.client:
            return {
                "agent": "disease_agent",
                "disease": "",
                "confidence": 0,
                "urgency": "low",
                "urdu_message": "ابھی تشخیص دستیاب نہیں ہے، براہ کرم بعد میں کوشش کریں۔",
                "suggestions": [],
            }

        mime = mime_type or "image/jpeg"
        parts = [
            DISEASE_AGENT_PROMPT,
            f"Farmer message: {message or ''}",
            {"mime_type": mime, "data": image_bytes},
            "Return JSON only without code fences.",
        ]
        result = await asyncio.to_thread(self.client.generate_json, parts)
        if not isinstance(result, dict):
            return {
                "agent": "disease_agent",
                "disease": "",
                "confidence": 0,
                "urgency": "low",
                "urdu_message": "تصویر واضح نہیں ہے، براہ کرم صاف تصویر دوبارہ بھیجیں۔",
                "suggestions": [],
            }

        result.setdefault("agent", "disease_agent")
        result.setdefault("disease", "")
        result.setdefault("confidence", 0)
        result.setdefault("urgency", "low")
        result.setdefault("urdu_message", "تصویر واضح نہیں ہے، براہ کرم صاف تصویر دوبارہ بھیجیں۔")
        if not isinstance(result.get("suggestions"), list):
            result["suggestions"] = []
        return result

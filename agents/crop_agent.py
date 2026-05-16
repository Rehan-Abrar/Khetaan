from __future__ import annotations

import asyncio

from agents.prompts import DISEASE_AGENT_PROMPT, DISEASE_TEXT_PROMPT
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
        language: str = "roman_urdu",
    ) -> dict:
        if not image_bytes:
            return self._build_missing_image_response(language)

        if not self.client:
            return self._build_not_available_response(language)

        mime = mime_type or "image/jpeg"
        parts = [
            DISEASE_AGENT_PROMPT,
            f"Farmer message: {message or ''}",
            self._language_instruction(language),
            {"mime_type": mime, "data": image_bytes},
            "Return JSON only without code fences.",
        ]
        result = await asyncio.to_thread(self.client.generate_json, parts)
        if not isinstance(result, dict):
            return self._build_unclear_response(language)

        result.setdefault("agent", "disease_agent")
        result.setdefault("disease", "")
        result.setdefault("confidence", 0)
        result.setdefault("urgency", "low")
        result.setdefault("urdu_message", self._fallback_message(language))
        if not isinstance(result.get("suggestions"), list):
            result["suggestions"] = []

        # Normalize confidence to 0-100 (some models return 0.0-1.0)
        conf = result.get("confidence", 0)
        if isinstance(conf, float) and conf <= 1.0:
            result["confidence"] = int(conf * 100)

        if self._looks_unclear(result):
            return self._build_unclear_response(language)

        return result

    async def diagnose_text(self, description: str, language: str = "roman_urdu") -> dict:
        description = description or ""
        if not self.client:
            return self._build_photo_needed_response(language)

        parts = [
            DISEASE_TEXT_PROMPT,
            f"Farmer message: {description}",
            self._language_instruction(language),
            "Return JSON only without code fences.",
        ]
        result = await asyncio.to_thread(self.client.generate_json, parts)
        if not isinstance(result, dict):
            return self._build_photo_needed_response(language)

        result.setdefault("agent", "disease_agent")
        result.setdefault("disease", "")
        result.setdefault("confidence", 0)
        result.setdefault("urgency", "low")
        result.setdefault("urdu_message", self._build_photo_needed_response(language)["urdu_message"])
        if not isinstance(result.get("suggestions"), list):
            result["suggestions"] = []
        return result

    @staticmethod
    def _looks_unclear(result: dict) -> bool:
        confidence = result.get("confidence", 0)
        disease = str(result.get("disease", "")).strip().lower()
        message = str(result.get("urdu_message", "")).strip().lower()

        # Normalize confidence to 0-100 scale (some models return 0-1 floats)
        if isinstance(confidence, float) and confidence <= 1.0:
            confidence = confidence * 100

        if isinstance(confidence, (int, float)) and confidence < 35:
            return True

        unclear_markers = [
            "clear photo",
            "clearer image",
            "tasveer clear nahi",
            "dubara clear photo",
            "photo bhejein",
            "image unclear",
        ]
        if any(marker in message for marker in unclear_markers):
            return True

        if not disease:
            return True

        return False

    @staticmethod
    def _language_instruction(language: str) -> str:
        if language == "english":
            return "Reply in English."
        return "Reply in Roman Urdu using Latin letters only. Do not use Urdu script."

    @staticmethod
    def _fallback_message(language: str) -> str:
        if language == "english":
            return "I analyzed the photo and prepared a farming-safe diagnosis."
        return "Maine tasveer dekh kar farming-safe tashkhees tayyar kar di hai."

    @staticmethod
    def _build_missing_image_response(language: str) -> dict:
        if language == "english":
            message = "Please send a clear crop photo so I can diagnose it."
        else:
            message = "Meherbani, fasal ki clear tasveer bhejein taa ke tashkhees ho sake."
        return {
            "agent": "disease_agent",
            "disease": "",
            "confidence": 0,
            "urgency": "low",
            "urdu_message": message,
            "suggestions": [],
        }

    @staticmethod
    def _build_not_available_response(language: str) -> dict:
        if language == "english":
            message = "Diagnosis is not available right now. Please try again later."
        else:
            message = "Abhi tashkhees available nahi, baad mein koshish karein."
        return {
            "agent": "disease_agent",
            "disease": "",
            "confidence": 0,
            "urgency": "low",
            "urdu_message": message,
            "suggestions": [],
        }

    @staticmethod
    def _build_unclear_response(language: str) -> dict:
        if language == "english":
            message = "The photo is unclear. Please send a clearer image."
        else:
            message = "Tasveer clear nahi hai, meherbani dubara clear photo bhejein."
        return {
            "agent": "disease_agent",
            "disease": "",
            "confidence": 0,
            "urgency": "low",
            "urdu_message": message,
            "suggestions": [],
        }

    @staticmethod
    def _build_photo_needed_response(language: str) -> dict:
        if language == "english":
            message = "I can help better with a crop photo. Please send one if possible."
        else:
            message = "Behtar tashkhees ke liye fasal ki tasveer bhej dein."
        return {
            "agent": "disease_agent",
            "disease": "",
            "confidence": 0,
            "urgency": "low",
            "urdu_message": message,
            "suggestions": [],
        }
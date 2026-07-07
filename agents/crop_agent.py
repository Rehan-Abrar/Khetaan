from __future__ import annotations

import asyncio
from pathlib import Path

from agents.prompts import DISEASE_AGENT_PROMPT, DISEASE_TEXT_PROMPT
from utils.gemini_client import GeminiClient


class CropAgent:
    def __init__(self, model_name: str | None = None) -> None:
        try:
            self.client = GeminiClient(model_name=model_name)
        except RuntimeError:
            self.client = None
        self.reference_images = self._load_reference_images()

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
        compressed_bytes, compressed_mime = self._compress_image(image_bytes, mime)
        parts = [
            DISEASE_AGENT_PROMPT,
            f"Farmer message: {message or ''}",
            self._language_instruction(language),
        ]

        # Removed reference images to drastically save tokens and prevent Groq 429 TPM limits.


        parts.extend(
            [
                "Farmer crop photo to diagnose:",
                {"mime_type": compressed_mime, "data": compressed_bytes},
                "Return JSON only without code fences.",
            ]
        )
        result = await asyncio.to_thread(self.client.generate_json, parts)
        if not isinstance(result, dict):
            # generate_json returned None — most likely a quota/API error,
            # not an unclear photo. Return an honest service-unavailable reply.
            return self._build_service_error_response(language)

        result.setdefault("agent", "disease_agent")
        result.setdefault("disease", "")
        result.setdefault("confidence", 0)
        result.setdefault("urgency", "low")
        result.setdefault("urdu_message", self._fallback_message(language))
        if not isinstance(result.get("suggestions"), list):
            result["suggestions"] = []

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
    def _compress_image(
        image_bytes: bytes,
        mime_type: str,
    ) -> tuple[bytes, str]:
        from PIL import Image
        import io
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            return buf.getvalue(), "image/jpeg"
        except Exception:
            return image_bytes, mime_type

    @staticmethod
    def _guess_mime_type(path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".png":
            return "image/png"
        return "image/jpeg"

    def _label_reference(self, filename: str) -> str:
        lower = filename.lower()
        if "wheat" in lower and "rust" in lower:
            return "Wheat Leaf Rust"
        if "cotton" in lower and "curl" in lower:
            return "Cotton Leaf Curl Virus"
        if "aphid" in lower:
            return "Aphids"
        return "Reference"

    def _load_reference_images(self) -> list[dict[str, str | bytes]]:
        root = Path(__file__).resolve().parent.parent
        ref_dir = root / "reference_images"
        if not ref_dir.exists():
            return []

        images: list[dict[str, str | bytes]] = []
        seen_labels: set[str] = set()
        for path in sorted(ref_dir.glob("*.jpg")) + sorted(ref_dir.glob("*.jpeg")) + sorted(ref_dir.glob("*.png")):
            label = self._label_reference(path.name)
            # Keep only the first image per disease class to stay within Groq's 5-image limit
            # (user photo counts as 1, so we allow max 3 reference images = 4 total < 5)
            if label in seen_labels:
                continue
            seen_labels.add(label)
            if len(images) >= 3:
                break
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            mime = self._guess_mime_type(path)
            compressed, compressed_mime = self._compress_image(raw, mime)
            images.append(
                {
                    "filename": path.name,
                    "label": label,
                    "mime_type": compressed_mime,
                    "data": compressed,
                }
            )
        return images

    @staticmethod
    def _looks_unclear(result: dict) -> bool:
        confidence = result.get("confidence", 0)
        disease = str(result.get("disease", "")).strip().lower()

        # Empty disease field — genuinely no result
        if not disease:
            return True

        # Explicitly unclear or unknown
        if disease in ("unclear", "unknown"):
            # Only treat as unclear if confidence is also very low
            if isinstance(confidence, (int, float)) and confidence < 30:
                return True
            # If Gemini says "unclear" but confidence is reasonable,
            # trust the urdu_message it wrote and pass through
            return False

        # Very low confidence on any disease — image likely unusable
        if isinstance(confidence, (int, float)) and confidence < 25:
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

    @staticmethod
    def _build_service_error_response(language: str) -> dict:
        if language == "english":
            message = "Diagnosis service is temporarily unavailable. Please try again in a few minutes."
        else:
            message = "Tashkhees ki service abhi dastiyab nahi. Thori dair baad dobara koshish karein."
        return {
            "agent": "disease_agent",
            "disease": "",
            "confidence": 0,
            "urgency": "low",
            "urdu_message": message,
            "suggestions": [],
        }
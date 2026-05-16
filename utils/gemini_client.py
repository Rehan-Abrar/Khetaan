from __future__ import annotations

import json
import os
from typing import Any

import google.generativeai as genai

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    cleaned = text.strip().replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    if start == -1:
        return None

    depth = 0
    end = None
    for index in range(start, len(cleaned)):
        char = cleaned[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break

    if end is None:
        return None

    snippet = cleaned[start:end]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError:
        return None


class GeminiClient:
    def __init__(self, model_name: str | None = None) -> None:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        genai.configure(api_key=api_key)
        self.model_name = model_name or DEFAULT_MODEL
        self.model = genai.GenerativeModel(self.model_name)

    def generate_json(
        self,
        parts: list[Any],
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
    ) -> dict[str, Any] | None:
        try:
            response = self.model.generate_content(
                parts,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                },
            )
        except Exception:
            return None

        text = getattr(response, "text", "") or ""
        return _extract_json_object(text)

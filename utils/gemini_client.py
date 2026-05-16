from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")


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


def _load_api_keys() -> list[str]:
    """Load all available API keys from env (GEMINI_API_KEY, GEMINI_API_KEY1, GEMINI_API_KEY2, ...)."""
    keys: list[str] = []
    # Primary key
    primary = os.getenv("GEMINI_API_KEY", "").strip()
    if primary:
        keys.append(primary)
    # Additional keys: GEMINI_API_KEY1, GEMINI_API_KEY2, ...
    for i in range(1, 10):
        key = os.getenv(f"GEMINI_API_KEY{i}", "").strip()
        if key:
            keys.append(key)
    return keys


class GeminiClient:
    def __init__(self, model_name: str | None = None) -> None:
        self.api_keys = _load_api_keys()
        if not self.api_keys:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        self.model_name = model_name or DEFAULT_MODEL
        self._key_index = 0

    def _get_client(self) -> genai.Client:
        return genai.Client(api_key=self.api_keys[self._key_index])

    def _next_key(self) -> bool:
        """Rotate to the next API key. Returns False if all keys exhausted."""
        if self._key_index + 1 < len(self.api_keys):
            self._key_index += 1
            return True
        return False

    def generate_json(
        self,
        parts: list[Any],
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> dict[str, Any] | None:
        # Build content parts for the new SDK
        content_parts: list[Any] = []
        for part in parts:
            if isinstance(part, str):
                if part:
                    content_parts.append(part)
            elif isinstance(part, dict) and "mime_type" in part and "data" in part:
                content_parts.append(
                    types.Part.from_bytes(
                        data=part["data"],
                        mime_type=part["mime_type"],
                    )
                )

        # Try each key until one works
        self._key_index = 0
        while True:
            try:
                # Create a fresh client per call — genai.Client is not thread-safe when reused
                client = genai.Client(api_key=self.api_keys[self._key_index])
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=content_parts,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                    ),
                )
                text = response.text or ""
                return _extract_json_object(text)

            except Exception as exc:
                err = str(exc)
                # On rate limit, try the next key
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    if self._next_key():
                        continue
                # Any other error or all keys exhausted
                return None

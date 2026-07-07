from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

from google import genai
from google.genai import types

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


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


def _get_api_keys() -> list[str]:
    """Get all available API keys from environment."""
    keys = []
    # Primary key
    primary = os.getenv("GEMINI_API_KEY", "").strip()
    if primary:
        keys.append(primary)
    # Fallback keys
    for i in range(1, 10):  # Support up to GEMINI_API_KEY9
        fallback = os.getenv(f"GEMINI_API_KEY{i}", "").strip()
        if fallback:
            keys.append(fallback)
    return keys


class GeminiClient:
    _last_failure_time: float = 0.0
    _cooldown_seconds: float = 45.0  # Cooldown period in seconds if all keys are exhausted

    def __init__(self, model_name: str | None = None) -> None:
        self.api_keys = _get_api_keys()
        if not self.api_keys:
            raise RuntimeError("No GEMINI_API_KEY found in environment.")
        self.current_key_index = 0
        self.client = genai.Client(api_key=self.api_keys[self.current_key_index])
        self.model_name = model_name or DEFAULT_MODEL

    def _rotate_key(self) -> bool:
        """Rotate to next API key. Returns True if rotation succeeded, False if no more keys."""
        self.current_key_index += 1
        if self.current_key_index >= len(self.api_keys):
            return False
        self.client = genai.Client(api_key=self.api_keys[self.current_key_index])
        print(f"[GeminiClient] Rotated to API key #{self.current_key_index + 1}", file=sys.stderr)
        return True

    def generate_json(
        self,
        parts: list[Any],
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
    ) -> dict[str, Any] | None:
        # Check circuit breaker
        now = time.time()
        if now - GeminiClient._last_failure_time < GeminiClient._cooldown_seconds:
            print("[GeminiClient] Circuit breaker is open. Fast-failing request.", file=sys.stderr)
            return None

        # Convert parts to google.genai content format
        contents: list[Any] = []
        for part in parts:
            if isinstance(part, str):
                contents.append(part)
            elif isinstance(part, dict) and "mime_type" in part and "data" in part:
                contents.append(
                    types.Part.from_bytes(
                        data=part["data"],
                        mime_type=part["mime_type"],
                    )
                )
            else:
                contents.append(str(part))

        # Try only the configured model
        models_to_try = [self.model_name]

        response = None
        max_overload_retries = 3
        base_delay_seconds = 0.8
        for model in models_to_try:
            # Try all API keys for this model
            keys_tried = 0
            while keys_tried < len(self.api_keys):
                overload_attempts = 0
                while True:
                    try:
                        response = self.client.models.generate_content(
                            model=model,
                            contents=contents,
                            config=types.GenerateContentConfig(
                                temperature=temperature,
                                max_output_tokens=max_output_tokens,
                            ),
                        )
                        break  # success — stop trying
                    except Exception as exc:
                        exc_name = type(exc).__name__
                        exc_str = str(exc)
                        exc_lower = exc_str.lower()

                        is_rate_limit = (
                            "429" in exc_str
                            or "resource_exhausted" in exc_lower
                            or "quota" in exc_lower
                        )
                        is_overloaded = ("503" in exc_str or "unavailable" in exc_lower)

                        if is_overloaded and overload_attempts < max_overload_retries:
                            overload_attempts += 1
                            delay = base_delay_seconds * (2 ** (overload_attempts - 1))
                            time.sleep(delay)
                            continue

                        if is_rate_limit:
                            if self._rotate_key():
                                keys_tried += 1
                                time.sleep(0.5)
                                break

                            error_preview = exc_str[:200] if len(exc_str) > 200 else exc_str
                            print(
                                f"[GeminiClient] {model} rate limit after all keys: {exc_name}: {error_preview}",
                                file=sys.stderr,
                            )
                            keys_tried = len(self.api_keys)
                            break

                        if is_overloaded:
                            print(
                                f"[GeminiClient] {model} overloaded after retries.",
                                file=sys.stderr,
                            )
                        else:
                            error_preview = exc_str[:200] if len(exc_str) > 200 else exc_str
                            print(
                                f"[GeminiClient] {model} error: {exc_name}: {error_preview}",
                                file=sys.stderr,
                            )
                        keys_tried = len(self.api_keys)
                        break

                if response is not None:
                    break

            if response is not None:
                break

        if response is None:
            # Tripped circuit breaker
            GeminiClient._last_failure_time = time.time()
            return None

        text = response.text or ""
        return _extract_json_object(text)


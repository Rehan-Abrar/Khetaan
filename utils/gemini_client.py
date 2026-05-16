from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

from google import genai
from google.genai import types

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODEL = "gemini-2.0-flash"


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
    # TEMPORARY: Only use GEMINI_API_KEY3 for testing
    key3 = os.getenv("GEMINI_API_KEY3", "").strip()
    if key3:
        keys.append(key3)
        return keys
    
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

        # Try primary model, fall back to gemini-2.0-flash on 503 overload
        models_to_try = [self.model_name]
        if self.model_name != FALLBACK_MODEL:
            models_to_try.append(FALLBACK_MODEL)

        response = None
        for model in models_to_try:
            # Try all API keys for this model
            keys_tried = 0
            while keys_tried < len(self.api_keys):
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
                    
                    # Check if it's a rate limit / quota error
                    is_rate_limit = (
                        "429" in exc_str
                        or "RESOURCE_EXHAUSTED" in exc_str
                        or "quota" in exc_str.lower()
                    )
                    
                    # Only log first 200 chars of error to avoid spam
                    error_preview = exc_str[:200] if len(exc_str) > 200 else exc_str
                    print(
                        f"[GeminiClient] {model} (key #{self.current_key_index + 1}) error: {exc_name}: {error_preview}",
                        file=sys.stderr,
                    )
                    
                    # If rate limited, try rotating to next key
                    if is_rate_limit:
                        if self._rotate_key():
                            keys_tried += 1
                            time.sleep(0.5)  # Brief delay before retry
                            continue  # retry with new key
                        else:
                            # No more keys to try
                            break
                    else:
                        # Non-rate-limit error, don't rotate key, just try next model
                        break
                
                keys_tried += 1
            
            if response is not None:
                break  # Got a successful response

        if response is None:
            return None

        text = response.text or ""
        return _extract_json_object(text)

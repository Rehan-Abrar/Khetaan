from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CACHE_PATH = Path("data/mandi_cache.json")


def scrape_punjab_mandi(language: str = "roman_urdu") -> list[dict[str, Any]]:
    """Load prices from cache. Always returns a plain list of price dicts."""
    if not CACHE_PATH.exists():
        return []
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        prices = data.get("prices", [])
        return prices if isinstance(prices, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_cache(prices: list[dict[str, Any]]) -> None:
    CACHE_PATH.parent.mkdir(exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"updated": "2026-05-16T08:20:51Z", "prices": prices}, f, ensure_ascii=False)

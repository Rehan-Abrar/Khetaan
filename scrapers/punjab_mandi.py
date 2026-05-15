from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CACHE_PATH = Path("data/mandi_cache.json")


def scrape_punjab_mandi() -> list[dict[str, Any]]:
    if not CACHE_PATH.exists():
        return []

    try:
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    prices = payload.get("prices", []) if isinstance(payload, dict) else []
    return prices if isinstance(prices, list) else []

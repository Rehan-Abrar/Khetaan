"""
Punjab Mandi price scraper — amis.pk Daily Market Changes
Source: http://www.amis.pk/Daily%20Market%20Changes.aspx
Prices are in Rs / 100 kg (FQP / Average wholesale price).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

MANDI_URL = "http://www.amis.pk/Daily%20Market%20Changes.aspx"
CACHE_PATH = Path("data/mandi_cache.json")
CACHE_TTL_HOURS = 6  # refresh cache if older than this

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

# Cities we care about (must match amis.pk spelling exactly)
TARGET_CITIES = {
    "Lahore",
    "Faisalabad",
    "Multan",
    "Rawalpindi",
    "Gujranwala",
    "Sargodha",
    "BahawalPur",
    "Sialkot",
}

# Crop keywords — any crop whose name contains one of these (case-insensitive)
TARGET_CROP_KEYWORDS = [
    "wheat",
    "cotton",
    "seed cotton",
    "rice",
    "maize",
    "potato",
    "onion",
    "tomato",
    "sugar",
    "gram",
    "chanay",
    "chana",
]

# Hardcoded fallback — used when both scraper and cache fail
FALLBACK_PRICES: list[dict[str, Any]] = [
    {"city": "Lahore",      "crop": "Wheat",            "price_today": "4200", "price_yesterday": "4200", "unit": "Rs/100kg"},
    {"city": "Faisalabad",  "crop": "Wheat",            "price_today": "4150", "price_yesterday": "4150", "unit": "Rs/100kg"},
    {"city": "Multan",      "crop": "Wheat",            "price_today": "4100", "price_yesterday": "4100", "unit": "Rs/100kg"},
    {"city": "Multan",      "crop": "Seed Cotton(Phutti)", "price_today": "9000", "price_yesterday": "9000", "unit": "Rs/100kg"},
    {"city": "Gujranwala",  "crop": "Rice Basmati Super (New)", "price_today": "28000", "price_yesterday": "28000", "unit": "Rs/100kg"},
    {"city": "Lahore",      "crop": "Potato Fresh",     "price_today": "1800", "price_yesterday": "1800", "unit": "Rs/100kg"},
    {"city": "Lahore",      "crop": "Onion",            "price_today": "5500", "price_yesterday": "5500", "unit": "Rs/100kg"},
    {"city": "Lahore",      "crop": "Tomato",           "price_today": "6000", "price_yesterday": "6000", "unit": "Rs/100kg"},
    {"city": "Lahore",      "crop": "Sugar",            "price_today": "9500", "price_yesterday": "9500", "unit": "Rs/100kg"},
]


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _load_cache() -> list[dict[str, Any]]:
    """Return cached prices if the cache exists and is fresh enough."""
    if not CACHE_PATH.exists():
        return []
    try:
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return []

        updated_str = payload.get("updated")
        if updated_str:
            updated_at = datetime.fromisoformat(updated_str)
            if datetime.now() - updated_at > timedelta(hours=CACHE_TTL_HOURS):
                logger.info("Mandi cache is stale, will refresh.")
                return []  # stale — trigger a fresh scrape

        prices = payload.get("prices", [])
        return prices if isinstance(prices, list) else []
    except Exception as exc:
        logger.warning("Cache read failed: %s", exc)
        return []


def _save_cache(prices: list[dict[str, Any]]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated": datetime.now().isoformat(),
        "prices": prices,
    }
    CACHE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Mandi cache saved: %d entries", len(prices))


# ── Scraper ───────────────────────────────────────────────────────────────────

def _is_target_crop(crop_name: str) -> bool:
    lower = crop_name.lower()
    return any(kw in lower for kw in TARGET_CROP_KEYWORDS)


def _scrape_live() -> list[dict[str, Any]]:
    """
    Fetch the Daily Market Changes page and parse the GridView1 table.
    Returns a list of price dicts, or [] on failure.
    """
    try:
        resp = requests.get(MANDI_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("amis.pk fetch failed: %s", exc)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # The price table is an ASP.NET GridView rendered as a plain <table>
    grid = soup.find("table", id=lambda x: x and "GridView1" in x)
    if not grid:
        logger.warning("GridView1 table not found on amis.pk page.")
        return []

    rows = grid.find_all("tr")
    if len(rows) < 2:
        logger.warning("GridView1 has no data rows.")
        return []

    prices: list[dict[str, Any]] = []

    for row in rows[1:]:  # skip header row
        cols = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cols) < 4:
            continue

        city       = cols[0].strip()
        crop       = cols[1].strip()
        price_today     = cols[2].strip()
        price_yesterday = cols[3].strip()
        change     = cols[4].strip() if len(cols) > 4 else ""

        # Filter to target cities and crops
        if city not in TARGET_CITIES:
            continue
        if not _is_target_crop(crop):
            continue

        prices.append({
            "city":             city,
            "crop":             crop,
            "price_today":      price_today,
            "price_yesterday":  price_yesterday,
            "change":           change,
            "unit":             "Rs/100kg",
        })

    logger.info("Scraped %d target price entries from amis.pk", len(prices))
    return prices


# ── Public API ────────────────────────────────────────────────────────────────

def scrape_punjab_mandi() -> list[dict[str, Any]]:
    """
    Return today's mandi prices for target crops and cities.

    Priority:
      1. Fresh cache (< 6 hours old)
      2. Live scrape from amis.pk  → saved to cache
      3. Stale cache (any age)
      4. Hardcoded fallback prices
    """
    # 1. Try fresh cache first
    cached = _load_cache()
    if cached:
        logger.info("Returning %d prices from cache.", len(cached))
        return cached

    # 2. Live scrape
    live = _scrape_live()
    if live:
        _save_cache(live)
        return live

    # 3. Stale cache (ignore TTL)
    if CACHE_PATH.exists():
        try:
            payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            stale = payload.get("prices", [])
            if stale:
                logger.warning("Using stale cache as fallback.")
                return stale
        except Exception:
            pass

    # 4. Hardcoded fallback
    logger.warning("Using hardcoded fallback prices.")
    return FALLBACK_PRICES

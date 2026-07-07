from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

CACHE_PATH = Path("data/mandi_cache.json")
BASE_URL = "http://www.amis.pk"
LIST_URL = f"{BASE_URL}/BrowsePrices.aspx?searchType=0"

TARGET_CROPS = [
    "wheat", "گندم", "cotton", "کپاس", "rice", "چاول", "maize", "مکئی",
    "potato", "آلو", "onion", "پیاز", "tomato", "ٹماٹر", "apple", "نارنگی",
    "banana", "کیلا", "mango", "آم", "grapes", "انگور", "orange", "لیمو"
]

TARGET_CITIES = ["lahore", "faisalabad", "rawalpindi", "multan", "okara", "islamabad", "peshawar", "karachi"]

FALLBACK_PRICES = [
    {"commodity": "گندم (Wheat)", "city": "Lahore", "min_price": "3200", "max_price": "3400", "unit": "per 40kg"},
    {"commodity": "گندم (Wheat)", "city": "Faisalabad", "min_price": "3150", "max_price": "3350", "unit": "per 40kg"},
    {"commodity": "کپاس (Cotton)", "city": "Multan", "min_price": "8500", "max_price": "9200", "unit": "per 40kg"},
    {"commodity": "چاول (Rice)", "city": "Gujranwala", "min_price": "4200", "max_price": "4800", "unit": "per 40kg"},
]


def _extract_viewstate(html: str) -> dict[str, str]:
    """Extract ASP.NET __VIEWSTATE and __EVENTVALIDATION from page."""
    viewstate = re.search(r'id="__VIEWSTATE" value="([^"]*)"', html)
    viewstategen = re.search(r'id="__VIEWSTATEGENERATOR" value="([^"]*)"', html)
    eventval = re.search(r'id="__EVENTVALIDATION" value="([^"]*)"', html)
    
    result = {}
    if viewstate:
        result["__VIEWSTATE"] = viewstate.group(1)
    if viewstategen:
        result["__VIEWSTATEGENERATOR"] = viewstategen.group(1)
    if eventval:
        result["__EVENTVALIDATION"] = eventval.group(1)
    return result


def _get_all_commodities() -> list[dict[str, str]]:
    """Get all commodities and their URLs from the list page."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": BASE_URL
    }
    
    try:
        with httpx.Client(headers=headers, timeout=20) as client:
            resp = client.get(LIST_URL)
            resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"id": "ctl00_cphPage_commoditiesList"})
        
        if not table:
            return []
        
        commodities = []
        for link in table.find_all("a", href=True):
            href = link["href"]
            # Extract commodityId from URL
            match = re.search(r'commodityId=(\d+)', href)
            if match:
                commodities.append({
                    "name": link.get_text(strip=True),
                    "url": href if href.startswith("http") else f"{BASE_URL}{href}",
                    "commodityId": match.group(1)
                })
        
        return commodities
    
    except Exception as e:
        print(f"[MandiScraper] Error fetching commodities: {e}")
        return []


def _parse_price_table(html: str) -> list[dict[str, Any]]:
    """Parse the price table from commodity page."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "ModulePrices_GridView1"})
    
    if not table:
        return []
    
    prices = []
    rows = table.find_all("tr")[1:]  # skip header
    
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        
        crop = cells[0].get_text(strip=True)
        if not crop:
            continue
        
        # Get prices from all city columns
        city_prices = {}
        for i, city in enumerate(["Lahore", "Faisalabad", "Rawalpindi", "Multan", "Okara"]):
            if i + 1 < len(cells):
                price = cells[i + 1].get_text(strip=True)
                if price and price != "0" and price.isdigit():
                    city_prices[city] = int(price)
        
        if city_prices:
            min_price = min(city_prices.values())
            max_price = max(city_prices.values())
            
            prices.append({
                "commodity": crop,
                "city": "Lahore",  # Default to first city
                "min_price": str(min_price),
                "max_price": str(max_price),
                "unit": "per 40kg",
                "city_prices": city_prices
            })
    
    return prices


def _is_target_crop(crop: str) -> bool:
    """Check if crop matches target crops."""
    crop_lower = crop.lower()
    return any(target in crop_lower for target in TARGET_CROPS)


def _format_urdu_response(prices: list[dict[str, Any]], language: str = "roman_urdu") -> str:
    """Format prices response in Roman Urdu or English."""
    if not prices:
        if language == "english":
            return "Mandi prices not available right now. Please try again later."
        return "منڈی ریٹ ابھی دستیاب نہیں۔ براہ کرم بعد میں دوبارہ کوشش کریں۔"
    
    lines = []
    if language == "english":
        lines.append("💰 Today's Mandi Prices (Punjab)")
    else:
        lines.append("💰 آج کے منڈی ریٹ (پنجاب)")
    
    for p in prices[:10]:  # max 10 entries
        commodity = p["commodity"]
        min_p = p["min_price"]
        max_p = p["max_price"]
        
        if language == "english":
            lines.append(f"🌾 {commodity}")
            lines.append(f"   Min: {min_p} PKR")
            lines.append(f"   Max: {max_p} PKR")
            lines.append("")
        else:
            lines.append(f"🌾 {commodity}")
            lines.append(f"   کم از کم: {min_p} روپے")
            lines.append(f"   زیادہ سے زیادہ: {max_p} روپے")
            lines.append("")
    
    if language == "english":
        lines.append("Source: Punjab AMIS | Today's date")
    else:
        lines.append("ماخذ: پنجاب AMIS | آج کی تاریخ")
    
    return "\n".join(lines)


def scrape_punjab_mandi(language: str = "roman_urdu") -> dict[str, Any]:
    """
    Load cached Punjab AMIS mandi prices to avoid heavy live scraping in web request threads.
    """
    try:
        if CACHE_PATH.exists():
            with open(CACHE_PATH, encoding="utf-8") as f:
                cache_data = json.load(f)
            prices = cache_data.get("prices", [])
            updated = cache_data.get("updated", datetime.now().isoformat())
            if prices:
                return {
                    "prices": prices,
                    "urdu_message": _format_urdu_response(prices, language),
                    "updated": updated,
                    "language": language
                }
    except Exception as e:
        print(f"[MandiScraper] Error loading cache: {e}")
        
    prices = FALLBACK_PRICES.copy()
    return {
        "prices": prices,
        "urdu_message": _format_urdu_response(prices, language),
        "updated": datetime.now().isoformat(),
        "language": language
    }


def scrape_punjab_mandi_live(language: str = "roman_urdu") -> dict[str, Any]:
    """
    Scrape Punjab AMIS for real mandi prices. (Run this only in background jobs/scripts).
    """
    all_prices: list[dict[str, Any]] = []
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": BASE_URL
        }
        
        # Step 1: Get all commodities
        commodities = _get_all_commodities()
        print(f"[MandiScraper] Found {len(commodities)} commodities")
        
        if not commodities:
            # Fallback if list page fails
            prices = FALLBACK_PRICES.copy()
            return {
                "prices": prices,
                "urdu_message": _format_urdu_response(prices, language),
                "updated": datetime.now().isoformat(),
                "language": language,
                "error": "Could not fetch commodity list"
            }
        
        # Step 2: Scrape each commodity
        with httpx.Client(headers=headers, timeout=20) as client:
            for i, commodity in enumerate(commodities):
                try:
                    # Add small delay to avoid rate limiting
                    if i > 0 and i % 5 == 0:
                        import time
                        time.sleep(0.5)
                    
                    resp = client.get(commodity["url"])
                    resp.raise_for_status()
                    
                    prices = _parse_price_table(resp.text)
                    if prices:
                        all_prices.extend(prices)
                        print(f"[MandiScraper] Scraped: {commodity['name']} ({len(prices)} entries)")
                    
                except httpx.NetworkError as e:
                    print(f"[MandiScraper] Network error for {commodity['name']}: {e}")
                    continue
                except Exception as e:
                    print(f"[MandiScraper] Error scraping {commodity['name']}: {e}")
                    continue
        
        # Filter to target crops
        all_prices = [p for p in all_prices if _is_target_crop(p["commodity"])]
        
        if not all_prices:
            prices = FALLBACK_PRICES.copy()
        else:
            prices = all_prices
            save_cache(prices)
        
        return {
            "prices": prices,
            "urdu_message": _format_urdu_response(prices, language),
            "updated": datetime.now().isoformat(),
            "language": language
        }
    
    except Exception as e:
        print(f"[MandiScraper] Error: {e}")
        prices = FALLBACK_PRICES.copy()
        return {
            "prices": prices,
            "urdu_message": _format_urdu_response(prices, language),
            "updated": datetime.now().isoformat(),
            "language": language,
            "error": str(e)
        }


def save_cache(prices: list[dict[str, Any]]) -> None:
    CACHE_PATH.parent.mkdir(exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"updated": datetime.now().isoformat(), "prices": prices}, f, ensure_ascii=False)


def load_cache() -> list[dict[str, Any]]:
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, encoding="utf-8") as f:
                return json.load(f).get("prices", [])
        except json.JSONDecodeError:
            return []
    return []

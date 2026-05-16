from __future__ import annotations

import asyncio
import json

from agents.prompts import MARKET_AGENT_PROMPT
from scrapers.punjab_mandi import scrape_punjab_mandi
from utils.gemini_client import GeminiClient


class MarketAgent:
    def __init__(self, model_name: str | None = None) -> None:
        try:
            self.client = GeminiClient(model_name=model_name)
        except RuntimeError:
            self.client = None

    async def get_prices(self, crop_filter: str | None = None, language: str = "roman_urdu") -> dict:
        prices = scrape_punjab_mandi()
        if crop_filter:
            filtered: list[dict] = []
            crop_filter_lower = crop_filter.lower()
            # Map Roman Urdu / Urdu crop names to English equivalents used in the data
            CROP_ALIASES: dict[str, list[str]] = {
                "gandum": ["wheat"],
                "گندم": ["wheat"],
                "chawal": ["rice"],
                "چاول": ["rice"],
                "kapas": ["cotton", "seed cotton"],
                "کپاس": ["cotton", "seed cotton"],
                "makai": ["maize"],
                "مکئی": ["maize"],
                "ganna": ["sugarcane", "sugar"],
                "گنا": ["sugarcane", "sugar"],
                "chanay": ["gram"],
                "چنے": ["gram"],
                "aloo": ["potato"],
                "آلو": ["potato"],
                "tamatar": ["tomato"],
                "ٹماٹر": ["tomato"],
                "piyaz": ["onion"],
                "پیاز": ["onion"],
            }
            # Resolve aliases — if the filter is a Roman Urdu word, expand it
            search_terms = CROP_ALIASES.get(crop_filter_lower, [crop_filter_lower])
            for item in prices:
                if not isinstance(item, dict):
                    continue
                item_crop_lower = str(item.get("crop", "")).lower()
                if any(term in item_crop_lower for term in search_terms):
                    filtered.append(item)
            # Only apply filter if it actually matched something
            if filtered:
                prices = filtered
            # else: ignore the filter and return all prices

        if not prices:
            return {
                "agent": "market_agent",
                "confidence": 0,
                "urgency": "low",
                "urdu_message": self._no_prices_message(language),
                "extra": {"crop": crop_filter or "", "price": ""},
            }

        if not self.client:
            return self._fallback_message(prices, crop_filter, language)

        context = {
            "crop_filter": crop_filter or "",
            "prices": [
                {
                    "city": p.get("city", ""),
                    "crop": p.get("crop", ""),
                    "price_today": p.get("price_today") or p.get("price", ""),
                    "price_yesterday": p.get("price_yesterday", ""),
                    "change": p.get("change", ""),
                    "unit": p.get("unit", "Rs/100kg"),
                }
                for p in prices
                if isinstance(p, dict)
            ],
        }
        parts = [
            MARKET_AGENT_PROMPT,
            f"Mandi price data (use only this data): {json.dumps(context, ensure_ascii=False)}",
            self._language_instruction(language),
            "Return JSON only without code fences.",
        ]
        result = await asyncio.to_thread(self.client.generate_json, parts)
        if not isinstance(result, dict):
            return self._fallback_message(prices, crop_filter, language)

        result.setdefault("agent", "market_agent")
        result.setdefault("confidence", 0)
        result.setdefault("urgency", "low")
        result.setdefault("urdu_message", self._simple_summary(prices, language))
        result.setdefault("extra", {"crop": crop_filter or "", "price": ""})
        return result

    def _fallback_message(self, prices: list[dict], crop_filter: str | None, language: str) -> dict:
        return {
            "agent": "market_agent",
            "confidence": 0,
            "urgency": "low",
            "urdu_message": self._simple_summary(prices, language),
            "extra": {"crop": crop_filter or "", "price": ""},
        }

    @staticmethod
    def _simple_summary(prices: list[dict], language: str) -> str:
        lines = []
        for item in prices[:8]:
            if not isinstance(item, dict):
                continue
            crop  = item.get("crop", "")
            city  = item.get("city", "")
            # Support both old schema (price) and new schema (price_today)
            price = item.get("price_today") or item.get("price", "")
            unit  = item.get("unit", "Rs/100kg")
            if crop and price:
                lines.append(f"  {crop} ({city}): {price} {unit}")

        if not lines:
            return MarketAgent._no_prices_message(language)

        if language == "english":
            return "Today's mandi rates (Punjab):\n" + "\n".join(lines)
        return "Aaj ke mandi rate (Punjab):\n" + "\n".join(lines)

    @staticmethod
    def _no_prices_message(language: str) -> str:
        if language == "english":
            return "Mandi rates are not available right now."
        return "Is waqt mandi rate available nahi."

    @staticmethod
    def _language_instruction(language: str) -> str:
        if language == "english":
            return "Reply in English."
        return "Reply in Roman Urdu using Latin letters only. Do not use Urdu script."

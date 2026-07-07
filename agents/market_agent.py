from __future__ import annotations

import asyncio
import json

from agents.prompts import MARKET_AGENT_PROMPT
from scrapers.punjab_mandi import scrape_punjab_mandi
from utils.gemini_client import GeminiClient


CROP_MAPPING = {
    "gandum": "wheat",
    "chawal": "rice",
    "kapas": "cotton",
    "makai": "maize",
    "ganna": "sugarcane",
    "chanay": "gram",
    "chana": "gram",
    "aloo": "potato",
    "tamatar": "tomato",
    "piyaz": "onion",
}


class MarketAgent:
    def __init__(self, model_name: str | None = None) -> None:
        try:
            self.client = GeminiClient(model_name=model_name)
        except RuntimeError:
            self.client = None

    async def get_prices(self, crop_filter: str | None = None, language: str = "roman_urdu") -> dict:
        result = scrape_punjab_mandi(language=language)
        prices = result.get("prices", []) if isinstance(result, dict) else []
        if not isinstance(prices, list):
            prices = []

        if crop_filter:
            filtered: list[dict] = []
            filter_lower = crop_filter.lower()
            mapped = CROP_MAPPING.get(filter_lower, filter_lower)
            for item in prices:
                if not isinstance(item, dict):
                    continue
                commodity = str(item.get("commodity", "") or item.get("crop", "")).lower()
                if filter_lower in commodity or mapped in commodity:
                    filtered.append(item)
            prices = filtered

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
            "prices": prices,
        }
        parts = [
            MARKET_AGENT_PROMPT,
            f"Mandi price data (use only this data): {json.dumps(context, ensure_ascii=False)}",
            self._language_instruction(language),
            "Return JSON only without code fences.",
        ]
        result_json = await asyncio.to_thread(self.client.generate_json, parts)
        if not isinstance(result_json, dict):
            return self._fallback_message(prices, crop_filter, language)

        result_json.setdefault("agent", "market_agent")
        result_json.setdefault("confidence", 0)
        result_json.setdefault("urgency", "low")
        result_json.setdefault("urdu_message", self._simple_summary(prices, language))
        result_json.setdefault("extra", {"crop": crop_filter or "", "price": ""})
        return result_json

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
        for item in prices[:5]:
            if not isinstance(item, dict):
                continue
            commodity = item.get("commodity", "") or item.get("crop", "")
            min_price = item.get("min_price", "")
            max_price = item.get("max_price", "")

            if min_price and max_price:
                price_str = f"Rs {min_price}-{max_price}"
            else:
                price_str = item.get("price", "")

            if commodity or price_str:
                lines.append(f"{commodity} {price_str}".strip())

        if not lines:
            return MarketAgent._no_prices_message(language)

        if language == "english":
            return "Mandi rates:\n" + "\n".join(lines)
        return "Mandi rate:\n" + "\n".join(lines)

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

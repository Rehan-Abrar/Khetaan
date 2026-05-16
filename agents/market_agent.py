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
            for item in prices:
                if not isinstance(item, dict):
                    continue
                if crop_filter in str(item.get("crop", "")):
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
        for item in prices[:5]:
            if not isinstance(item, dict):
                continue
            crop = item.get("crop", "")
            price = item.get("price", "")
            if crop or price:
                lines.append(f"{crop} {price}".strip())

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

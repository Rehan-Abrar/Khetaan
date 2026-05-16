from __future__ import annotations

import asyncio
import json
from typing import Any

from agents.prompts import MARKET_AGENT_PROMPT
from scrapers.punjab_mandi import scrape_punjab_mandi
from utils.gemini_client import GeminiClient


class MarketAgent:
    def __init__(self, model_name: str | None = None) -> None:
        try:
            self.client = GeminiClient(model_name=model_name)
        except RuntimeError:
            self.client = None

    async def get_prices(
        self,
        crop_filter: str | None = None,
        city_filter: str | None = None,
        language: str = "roman_urdu",
    ) -> dict:
        prices = scrape_punjab_mandi()
        
        # Apply filters
        if crop_filter:
            prices = [p for p in prices if crop_filter.lower() in p.get("crop", "").lower()]
        if city_filter:
            prices = [p for p in prices if city_filter.lower() in p.get("city", "").lower()]

        if not prices:
            return {
                "agent": "market_agent",
                "confidence": 0,
                "urgency": "low",
                "urdu_message": self._no_prices_message(language),
                "extra": {"crop": crop_filter or "", "city": city_filter or ""},
            }

        # Bypass Gemini entirely - use _format_response directly
        return {
            "agent": "market_agent",
            "confidence": 80,
            "urgency": "low",
            "urdu_message": self._format_response(prices, language),
            "extra": {"crop": crop_filter or "", "city": city_filter or ""},
        }

    def _fallback_message(
        self,
        prices: list[dict],
        crop_filter: str | None,
        city_filter: str | None,
        language: str,
    ) -> dict:
        return {
            "agent": "market_agent",
            "confidence": 0,
            "urgency": "low",
            "urdu_message": self._format_response(prices, language),
            "extra": {"crop": crop_filter or "", "city": city_filter or ""},
        }

    @staticmethod
    def _format_response(prices: list[dict], language: str) -> str:
        """Format prices with city names in Roman Urdu or English."""
        if not prices:
            return MarketAgent._no_prices_message(language)

        lines = []
        if language == "english":
            lines.append("💰 Today's Mandi Prices (Punjab)")
        else:
            lines.append("💰 Aaj ke Mandi Rate (Punjab)")

        # Group by crop
        crops: dict[str, list[dict]] = {}
        for item in prices:
            if not isinstance(item, dict):
                continue
            crop = item.get("commodity", "Unknown")
            if crop not in crops:
                crops[crop] = []
            crops[crop].append(item)

        for crop, items in list(crops.items())[:5]:  # Max 5 crops
            if language == "english":
                lines.append(f"\n🌾 {crop}")
            else:
                lines.append(f"\n🌾 {crop}")

            for item in items[:3]:  # Max 3 cities per crop
                city = item.get("city", "")
                min_p = item.get("min_price", "")
                max_p = item.get("max_price", "")

                if language == "english":
                    lines.append(f"   {city}: Min {min_p} PKR, Max {max_p} PKR")
                else:
                    lines.append(f"   {city}: Kam az kam {min_p} rupay, Zyada se zyada {max_p} rupay")

        if language == "english":
            lines.append("\nSource: Punjab AMIS | Today's date")
        else:
            lines.append("\nSource: Punjab AMIS | Aaj ki tarikh")

        return "\n".join(lines)

    @staticmethod
    def _no_prices_message(language: str) -> str:
        if language == "english":
            return "Mandi rates are not available right now. Please try again later."
        return "Aaj ke mandi rate abhi available nahi hain. Baad mein dobara koshish karein."

    @staticmethod
    def _language_instruction(language: str) -> str:
        if language == "english":
            return "Reply in English."
        return "Reply in Roman Urdu using Latin letters only. Do not use Urdu script."

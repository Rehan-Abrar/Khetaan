from __future__ import annotations

import asyncio
import re

from agents import (
    CropAgent,
    FallbackAgent,
    HelpAgent,
    MarketAgent,
    RomanUrduNormalizer,
    RouterAgent,
    WeatherAgent,
)
from utils.urdu_formatter import format_urdu_message


class Orchestrator:
    def __init__(self) -> None:
        self.router = RouterAgent()
        self.normalizer = RomanUrduNormalizer()
        self.crop = CropAgent()
        self.weather = WeatherAgent()
        self.market = MarketAgent()
        self.help = HelpAgent()
        self.fallback = FallbackAgent()

    async def route(
        self,
        message: str,
        image_bytes: bytes | None,
        sender: str,
        media_type: str | None = None,
    ) -> str:
        message = message or ""
        normalized = await self._normalize_message(message)
        router_result = await self.router.route(normalized, image_present=bool(image_bytes))
        agent_names = router_result.get("agents", []) if isinstance(router_result, dict) else []

        if isinstance(agent_names, list) and len(agent_names) > 1:
            agent_names = [name for name in agent_names if name != "help_agent"]

        tasks = []
        if "disease_agent" in agent_names:
            tasks.append(self.crop.diagnose(normalized, image_bytes, media_type))

        if "weather_agent" in agent_names:
            lat_lon = self._extract_lat_lon(message) or self._extract_lat_lon(normalized)
            lat, lon = lat_lon if lat_lon else (None, None)
            tasks.append(self.weather.advise(normalized, lat, lon))

        if "market_agent" in agent_names:
            crop_filter = self._detect_crop_filter(normalized)
            tasks.append(self.market.get_prices(crop_filter))

        if "help_agent" in agent_names:
            tasks.append(self.help.respond())

        if not tasks:
            tasks.append(self.fallback.respond(normalized))

        results = await asyncio.gather(*tasks)
        response = format_urdu_message(results)
        if response:
            return response

        fallback = await self.fallback.respond(normalized)
        return format_urdu_message([fallback])

    async def _normalize_message(self, message: str) -> str:
        if not message.strip():
            return message
        if self._contains_urdu(message):
            return message

        result = await self.normalizer.normalize(message)
        if isinstance(result, dict) and result.get("urdu"):
            return str(result["urdu"]).strip()
        return message

    @staticmethod
    def _contains_urdu(message: str) -> bool:
        return any("\u0600" <= char <= "\u06ff" for char in message)

    @staticmethod
    def _extract_lat_lon(message: str) -> tuple[float, float] | None:
        match = re.search(r"(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)", message)
        if not match:
            match = re.search(
                r"lat\s*[:=]\s*(-?\d{1,2}\.\d+).+lon\s*[:=]\s*(-?\d{1,3}\.\d+)",
                message,
                re.IGNORECASE,
            )
        if not match:
            return None
        lat = float(match.group(1))
        lon = float(match.group(2))
        if not (20.0 <= lat <= 40.0 and 60.0 <= lon <= 80.0):
            return None
        return lat, lon

    @staticmethod
    def _detect_crop_filter(message: str) -> str | None:
        crops = [
            "گندم",
            "چاول",
            "کپاس",
            "مکئی",
            "گنا",
            "چنے",
            "چنا",
            "آلو",
            "ٹماٹر",
            "پیاز",
            "cotton",
            "wheat",
            "rice",
            "maize",
            "potato",
            "tomato",
            "onion",
            "sugarcane",
        ]
        for crop in crops:
            if crop in message:
                return crop
        return None

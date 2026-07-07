from __future__ import annotations

import asyncio
import re
from collections import defaultdict

from agents import CropAgent, FallbackAgent, HelpAgent, MarketAgent, RouterAgent, WeatherAgent
from utils.urdu_formatter import format_urdu_message

MAX_HISTORY = 10
conversation_history: dict[str, list[dict[str, str]]] = defaultdict(list)

CITY_COORDS = {
    "lahore": (31.5204, 74.3587),
    "faisalabad": (31.4187, 73.0791),
    "multan": (30.1575, 71.5249),
    "rawalpindi": (33.5651, 73.0169),
    "gujranwala": (32.1877, 74.1945),
    "sialkot": (32.4945, 74.5229),
    "bahawalpur": (29.3956, 71.6836),
    "sargodha": (32.0836, 72.6711),
}

ENGLISH_HINTS = {
    "what",
    "how",
    "when",
    "where",
    "why",
    "please",
    "price",
    "market",
    "rate",
    "sell",
    "weather",
    "irrigation",
    "water",
    "disease",
    "crop",
    "help",
    "hello",
}

WEATHER_HINTS = {
    "بارش",
    "barish",
    "baarish",
    "pani",
    "paani",
    "aabpashi",
    "aabpaashi",
    "irrigation",
    "rain",
    "weather",
    "mausam",
    "mosam",
}


class Orchestrator:
    def __init__(self) -> None:
        self.router = RouterAgent()
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
        history = self._append_history(sender, "user", message or "[media]")
        language = self._detect_language(message)
        normalized = await self._normalize_message(message)

        # ── Fast-path: image with no meaningful text ──
        # Skip the Gemini router call (saves 5-10 s) so Meta doesn’t retry.
        if image_bytes and len(message.strip()) < 20:
            agent_names = ["disease_agent"]
        else:
            router_result = await self.router.route(
                normalized,
                image_present=bool(image_bytes),
                history=history,
            )
            agent_names = router_result.get("agents", []) if isinstance(router_result, dict) else []

            if self._looks_like_weather_question(message, normalized) and "weather_agent" not in agent_names:
                agent_names.append("weather_agent")

            # Don’t mix help_agent with other real agents
            if isinstance(agent_names, list) and len(agent_names) > 1:
                agent_names = [name for name in agent_names if name != "help_agent"]

        tasks = []
        if "disease_agent" in agent_names:
            if image_bytes:
                tasks.append(self.crop.diagnose(normalized, image_bytes, media_type, language))
            else:
                tasks.append(self.crop.diagnose_text(normalized, language))

        if "weather_agent" in agent_names:
            lat_lon = self._resolve_location(message, normalized, history)
            city_name = self._resolve_city(message, normalized, history)
            lat, lon = lat_lon if lat_lon else (None, None)
            tasks.append(self.weather.advise(normalized, lat, lon, city_name, language))

        if "market_agent" in agent_names:
            crop_filter = self._detect_crop_filter(normalized)
            tasks.append(self.market.get_prices(crop_filter, language))

        if "help_agent" in agent_names:
            tasks.append(self.help.respond(language))

        if not tasks:
            tasks.append(self.fallback.respond(normalized, language))

        results = await asyncio.gather(*tasks)

        disease_result = next(
            (item for item in results if isinstance(item, dict) and item.get("agent") == "disease_agent"),
            None,
        )
        weather_result = next(
            (item for item in results if isinstance(item, dict) and item.get("agent") == "weather_agent"),
            None,
        )

        if disease_result and not weather_result and self._is_fungal_risk(disease_result):
            lat_lon = self._resolve_location(message, normalized, history)
            city_name = self._resolve_city(message, normalized, history)
            if lat_lon:
                lat, lon = lat_lon
                weather_result = await self.weather.advise(normalized, lat, lon, city_name, language)
                results.append(weather_result)

        results = self._apply_cross_agent_rules(results, language)
        response = format_urdu_message(results, language=language)
        if response:
            self._append_history(sender, "assistant", response)
            return response

        fallback = await self.fallback.respond(normalized, language)
        response = format_urdu_message([fallback], language=language)
        self._append_history(sender, "assistant", response)
        return response

    async def _normalize_message(self, message: str) -> str:
        return message

    def _append_history(self, sender: str, role: str, content: str) -> list[dict[str, str]]:
        history = conversation_history[sender]
        if content:
            history.append({"role": role, "content": content})
        if len(history) > MAX_HISTORY:
            history[:] = history[-MAX_HISTORY:]
        return history

    @staticmethod
    def _detect_language(message: str) -> str:
        if not message:
            return "roman_urdu"
        words = set(re.findall(r"[a-zA-Z']+", message.lower()))
        if len(words & ENGLISH_HINTS) >= 2:
            return "english"
        return "roman_urdu"

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
    def _extract_city(message: str) -> str | None:
        msg = message.lower()
        for city in CITY_COORDS.keys():
            if city in msg:
                return city
        return None

    def _resolve_location(
        self,
        message: str,
        normalized: str,
        history: list[dict[str, str]],
    ) -> tuple[float, float] | None:
        lat_lon = self._extract_lat_lon(message) or self._extract_lat_lon(normalized)
        if lat_lon:
            return lat_lon

        city = self._extract_city(message) or self._extract_city(normalized)
        if not city:
            for item in reversed(history):
                city = self._extract_city(item.get("content", ""))
                if city:
                    break

        return CITY_COORDS.get(city) if city else None

    def _resolve_city(
        self,
        message: str,
        normalized: str,
        history: list[dict[str, str]],
    ) -> str | None:
        city = self._extract_city(message) or self._extract_city(normalized)
        if not city:
            for item in reversed(history):
                city = self._extract_city(item.get("content", ""))
                if city:
                    break

        if city:
            return city.title()
        return None

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
            "gandum",
            "chawal",
            "kapas",
            "makai",
            "ganna",
            "chanay",
            "aloo",
            "tamatar",
            "piyaz",
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

    @staticmethod
    def _looks_like_weather_question(message: str, normalized: str) -> bool:
        combined = f"{message} {normalized}".lower()
        return any(keyword in combined for keyword in WEATHER_HINTS)

    def _apply_cross_agent_rules(self, results: list[dict], language: str) -> list[dict]:
        disease_result = next(
            (item for item in results if isinstance(item, dict) and item.get("agent") == "disease_agent"),
            None,
        )
        weather_result = next(
            (item for item in results if isinstance(item, dict) and item.get("agent") == "weather_agent"),
            None,
        )

        if not disease_result or not weather_result:
            return results

        if not self._is_fungal_risk(disease_result):
            return results

        rain_chance = self._extract_rain_chance(weather_result)
        if rain_chance is None or rain_chance < 40:
            return results

        warning = self._fungal_warning(language)
        weather_message = (weather_result.get("urdu_message") or "").strip()
        if warning not in weather_message:
            weather_result["urdu_message"] = (weather_message + "\n\n" + warning).strip()
        weather_result["urgency"] = "high"
        return results

    @staticmethod
    def _extract_rain_chance(weather_result: dict) -> float | None:
        extra = weather_result.get("extra") if isinstance(weather_result, dict) else None
        raw = ""
        if isinstance(extra, dict):
            raw = extra.get("rain_chance", "") or ""
        if not raw:
            raw = weather_result.get("rain_chance", "") if isinstance(weather_result, dict) else ""

        matches = re.findall(r"\d+(?:\.\d+)?", str(raw))
        if not matches:
            return None
        try:
            return float(matches[0])
        except ValueError:
            return None

    @staticmethod
    def _is_fungal_risk(disease_result: dict) -> bool:
        if not isinstance(disease_result, dict):
            return False
        confidence = disease_result.get("confidence")
        if isinstance(confidence, (int, float)) and confidence < 40:
            return False

        disease_text = " ".join(
            [
                str(disease_result.get("disease", "")),
                str(disease_result.get("urdu_message", "")),
            ]
        ).lower()
        keywords = ["rust", "leaf rust", "curl", "fungal", "fungus", "zang", "curl", "patta mor"]
        return any(keyword in disease_text for keyword in keywords)

    @staticmethod
    def _fungal_warning(language: str) -> str:
        if language == "english":
            return "⚠️ With rain and disease, risk of spread is high. Stop irrigation and improve airflow."
        return "⚠️ Barish ke sath bimari phail sakti hai, aabpashi rokein aur hawa dari behtar karein."

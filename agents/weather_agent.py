from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx

from agents.prompts import WEATHER_AGENT_PROMPT
from utils.gemini_client import GeminiClient


class WeatherAgent:
    def __init__(self, model_name: str | None = None) -> None:
        try:
            self.client = GeminiClient(model_name=model_name)
        except RuntimeError:
            self.client = None

    async def advise(
        self,
        message: str | None,
        lat: float | None,
        lon: float | None,
        location_name: str | None = None,
        language: str = "roman_urdu",
    ) -> dict:
        if lat is None or lon is None:
            return {
                "agent": "weather_agent",
                "confidence": 0,
                "urgency": "low",
                "urdu_message": self._missing_location_message(language),
                "extra": {"temperature": "", "rain_chance": ""},
            }

        weather = await self._fetch_weather(lat, lon)
        if not weather:
            return {
                "agent": "weather_agent",
                "confidence": 0,
                "urgency": "low",
                "urdu_message": self._no_weather_message(language),
                "extra": {"temperature": "", "rain_chance": ""},
            }

        temperature = weather.get("temperature")
        humidity = weather.get("humidity")
        max_rain_chance = weather.get("max_rain_chance")

        return self._build_response(
            temperature=temperature,
            max_rain_chance=max_rain_chance,
            humidity=humidity,
            location_name=location_name,
            language=language,
        )

    async def _fetch_weather(self, lat: float, lon: float) -> dict[str, Any] | None:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m",
            "hourly": "precipitation_probability",
            "forecast_days": 1,
            "timezone": "auto",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception:
            return None

        current = data.get("current", {}) if isinstance(data, dict) else {}
        hourly = data.get("hourly", {}) if isinstance(data, dict) else {}
        temperature = current.get("temperature_2m")
        humidity = current.get("relative_humidity_2m")
        rain_values = hourly.get("precipitation_probability", []) or []
        max_rain = self._max_numeric(rain_values)

        return {
            "temperature": temperature,
            "humidity": humidity,
            "max_rain_chance": max_rain,
        }

    @staticmethod
    def _max_numeric(values: list[Any]) -> float | None:
        numeric = [value for value in values if isinstance(value, (int, float))]
        return max(numeric) if numeric else None

    @staticmethod
    def _format_extra(temperature: float | None, rain_chance: float | None, humidity: float | None = None) -> dict[str, str]:
        temp_str = f"{temperature}C" if isinstance(temperature, (int, float)) else ""
        rain_str = f"{rain_chance}%" if isinstance(rain_chance, (int, float)) else ""
        humidity_str = f"{humidity}%" if isinstance(humidity, (int, float)) else ""
        return {"temperature": temp_str, "rain_chance": rain_str, "humidity": humidity_str}

    def _build_response(
        self,
        temperature: float | None,
        max_rain_chance: float | None,
        humidity: float | None,
        location_name: str | None,
        language: str,
    ) -> dict:
        if temperature is None and max_rain_chance is None:
            return {
                "agent": "weather_agent",
                "confidence": 0,
                "urgency": "low",
                "urdu_message": self._no_weather_message(language),
                "extra": {"temperature": "", "rain_chance": "", "humidity": ""},
            }

        location_label = location_name or self._location_label(language)
        temp_str = self._temperature_phrase(temperature, language)
        rain_str = self._rain_phrase(max_rain_chance, language)

        if isinstance(max_rain_chance, (int, float)) and max_rain_chance >= 80:
            recommendation = self._rain_message("very_high", language)
            urgency = "high"
        elif isinstance(max_rain_chance, (int, float)) and max_rain_chance >= 60:
            recommendation = self._rain_message("high", language)
            urgency = "medium"
        elif isinstance(max_rain_chance, (int, float)) and max_rain_chance >= 40:
            recommendation = self._rain_message("medium", language)
            urgency = "low"
        elif isinstance(temperature, (int, float)) and temperature >= 36:
            recommendation = self._heat_message(language)
            urgency = "medium"
        else:
            recommendation = self._normal_message(language)
            urgency = "low"

        if language == "english":
            message = (
                f"{location_label} weather update:\n"
                f"Temperature: {temp_str}\n"
                f"Rain chance next 24h: {rain_str}\n\n"
                f"Irrigation advice: {recommendation}"
            )
        else:
            message = (
                f"{location_label} ka mausam:\n"
                f"Darja hararat: {temp_str}\n"
                f"Agle 24 ghanton mein barish ka imkaan: {rain_str}\n\n"
                f"Aabpashi mashwara: {recommendation}"
            )

        return {
            "agent": "weather_agent",
            "confidence": 50,
            "urgency": urgency,
            "urdu_message": message,
            "extra": self._format_extra(temperature, max_rain_chance, humidity),
        }

    @staticmethod
    def _location_label(language: str) -> str:
        return "Location" if language == "english" else "Ilaqe"

    @staticmethod
    def _temperature_phrase(temperature: float | None, language: str) -> str:
        if not isinstance(temperature, (int, float)):
            return "N/A"
        return f"{round(temperature, 1)} C" if language == "english" else f"{round(temperature, 1)} C"

    @staticmethod
    def _rain_phrase(max_rain_chance: float | None, language: str) -> str:
        if not isinstance(max_rain_chance, (int, float)):
            return "N/A"
        return f"{round(max_rain_chance)}%"

    @staticmethod
    def _missing_location_message(language: str) -> str:
        if language == "english":
            return "Please share your city or nearby area so I can give weather advice."
        return "Meherbani apna shehar ya qareebi ilaqa batain taa ke mausam ka mashwara mil sake."

    @staticmethod
    def _no_weather_message(language: str) -> str:
        if language == "english":
            return "Weather data is not available right now. Please try again later."
        return "Is waqt mausam ka data available nahi. Thori dair baad koshish karein."

    @staticmethod
    def _rain_message(level: str, language: str) -> str:
        if language == "english":
            if level == "very_high":
                return "Heavy rain is very likely. Do not irrigate right now."
            if level == "high":
                return "Rain chance is high. Stop irrigation for now."
            return "There is a chance of rain. Reduce irrigation."

        if level == "very_high":
            return "Barish ka imkan bohat zyada hai, abhi aabpashi na karein."
        if level == "high":
            return "Barish ka imkan zyada hai, aabpashi rokein."
        return "Barish ka imkan hai, pani kam dein."

    @staticmethod
    def _heat_message(language: str) -> str:
        if language == "english":
            return "It is very hot. Irrigate early morning or evening."
        return "Garmi zyada hai, pani subah ya shaam ko dein."

    @staticmethod
    def _normal_message(language: str) -> str:
        if language == "english":
            return "Weather looks normal. Irrigate as usual."
        return "Mausam theek hai, mamool ke mutabiq aabpashi karein."

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
    ) -> dict:
        if lat is None or lon is None:
            return {
                "agent": "weather_agent",
                "confidence": 0,
                "urgency": "low",
                "urdu_message": "براہ کرم اپنا شہر یا نزدیکی علاقہ بتائیں تاکہ موسم کا مشورہ دیا جا سکے۔",
                "extra": {"temperature": "", "rain_chance": ""},
            }

        weather = await self._fetch_weather(lat, lon)
        if not weather:
            return {
                "agent": "weather_agent",
                "confidence": 0,
                "urgency": "low",
                "urdu_message": "اس وقت موسم کا ڈیٹا دستیاب نہیں ہے۔ براہ کرم بعد میں کوشش کریں۔",
                "extra": {"temperature": "", "rain_chance": ""},
            }

        temperature = weather.get("temperature")
        humidity = weather.get("humidity")
        max_rain_chance = weather.get("max_rain_chance")

        if not self.client:
            return {
                "agent": "weather_agent",
                "confidence": 0,
                "urgency": "low",
                "urdu_message": "موسمی مشورہ ابھی دستیاب نہیں ہے، براہ کرم بعد میں کوشش کریں۔",
                "extra": self._format_extra(temperature, max_rain_chance),
            }

        context = {
            "temperature_c": temperature,
            "humidity_percent": humidity,
            "max_rain_chance_percent_next_24h": max_rain_chance,
            "message": message or "",
        }
        parts = [
            WEATHER_AGENT_PROMPT,
            f"Weather data (use only this data): {json.dumps(context, ensure_ascii=False)}",
            "Return JSON only without code fences.",
        ]
        result = await asyncio.to_thread(self.client.generate_json, parts)
        if not isinstance(result, dict):
            return {
                "agent": "weather_agent",
                "confidence": 0,
                "urgency": "low",
                "urdu_message": "اس وقت موسم کا مشورہ نہیں مل سکا۔ براہ کرم بعد میں دوبارہ پوچھیں۔",
                "extra": self._format_extra(temperature, max_rain_chance),
            }

        result.setdefault("agent", "weather_agent")
        result.setdefault("confidence", 0)
        result.setdefault("urgency", "low")
        result.setdefault("urdu_message", "اس وقت موسم کا مشورہ نہیں مل سکا۔")
        result.setdefault("extra", self._format_extra(temperature, max_rain_chance))
        return result

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
    def _format_extra(temperature: float | None, rain_chance: float | None) -> dict[str, str]:
        temp_str = f"{temperature}C" if isinstance(temperature, (int, float)) else ""
        rain_str = f"{rain_chance}%" if isinstance(rain_chance, (int, float)) else ""
        return {"temperature": temp_str, "rain_chance": rain_str}

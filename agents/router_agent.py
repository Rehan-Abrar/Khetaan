from __future__ import annotations

import asyncio
from typing import Any

from agents.prompts import ROUTER_PROMPT
from utils.gemini_client import GeminiClient

ALLOWED_AGENTS = {"disease_agent", "weather_agent", "market_agent", "help_agent"}
DISEASE_KEYWORDS = (
    "بیماری",
    "bimari",
    "bemari",
    "disease",
    "spots",
    "spot",
    "daag",
    "curl",
    "murjha",
    "murjhana",
    "phaphund",
    "fungal",
    "fungus",
    "زنگ",
    "کرل",
    "پتہ",
    "پتے",
    "patta",
    "patte",
    "leaf",
)
WEATHER_KEYWORDS = (
    "پانی",
    "بارش",
    "موسم",
    "weather",
    "pani",
    "aabpashi",
    "aabpaashi",
    "irrigation",
    "rain",
    "barish",
    "baarish",
)
MARKET_KEYWORDS = ("قیمت", "ریٹ", "منڈی", "rate", "price", "mandi", "market")
HELP_KEYWORDS = ("hello", "hi", "اسلام", "السلام", "help", "مدد", "salaam", "salam")


class RouterAgent:
    def __init__(self, model_name: str | None = None) -> None:
        try:
            self.client = GeminiClient(model_name=model_name)
        except RuntimeError:
            self.client = None

    async def route(
        self,
        message: str,
        image_present: bool,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        message = message or ""
        if not self.client:
            return self._fallback_route(message, image_present)

        history_lines = []
        if history:
            for item in history[-6:]:
                role = item.get("role", "")
                content = item.get("content", "")
                if content:
                    history_lines.append(f"{role.upper()}: {content}")
        history_text = "\n".join(history_lines)

        parts = [
            ROUTER_PROMPT,
            f"Message: {message}",
            f"Image present: {'yes' if image_present else 'no'}",
            f"Recent conversation:\n{history_text}" if history_text else "",
            "Return JSON only without code fences.",
        ]
        result = await asyncio.to_thread(self.client.generate_json, parts)
        if not result:
            return self._fallback_route(message, image_present)

        agents = result.get("agents", [])
        if not isinstance(agents, list):
            agents = []
        agents = [agent for agent in agents if agent in ALLOWED_AGENTS]

        if image_present and "disease_agent" not in agents:
            agents.append("disease_agent")

        if not agents:
            agents = ["help_agent"]

        priority = result.get("priority")
        if priority not in {"low", "medium", "high"}:
            priority = "low"

        return {
            "agents": agents,
            "needs_image_analysis": bool(image_present),
            "priority": priority,
        }

    def _fallback_route(self, message: str, image_present: bool) -> dict[str, Any]:
        msg_lower = message.lower()
        agents: list[str] = []

        if image_present:
            agents.append("disease_agent")

        if any(keyword in msg_lower or keyword in message for keyword in DISEASE_KEYWORDS):
            agents.append("disease_agent")

        if any(keyword in msg_lower or keyword in message for keyword in WEATHER_KEYWORDS):
            agents.append("weather_agent")

        if any(keyword in msg_lower or keyword in message for keyword in MARKET_KEYWORDS):
            agents.append("market_agent")

        if not agents and any(keyword in msg_lower or keyword in message for keyword in HELP_KEYWORDS):
            agents.append("help_agent")

        if not agents:
            agents.append("help_agent")

        return {
            "agents": agents,
            "needs_image_analysis": bool(image_present),
            "priority": "low",
        }

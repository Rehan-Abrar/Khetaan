from __future__ import annotations

from typing import Any

URGENCY_ORDER = {"high": 0, "medium": 1, "low": 2}
URGENCY_ALIASES = {
    "فوری": "high",
    "زیادہ": "high",
    "درمیانہ": "medium",
    "کم": "low",
}
SECTION_TITLES = {
    "roman_urdu": {
        "disease_agent": "🌿 Bimari",
        "weather_agent": "🌦 Mausam",
        "market_agent": "💰 Mandi rate",
        "help_agent": "ℹ️ Madad",
        "fallback_agent": "ℹ️ Rehnumai",
    },
    "english": {
        "disease_agent": "🌿 Disease",
        "weather_agent": "🌦 Weather",
        "market_agent": "💰 Mandi rates",
        "help_agent": "ℹ️ Help",
        "fallback_agent": "ℹ️ Guidance",
    },
}


def format_urdu_message(message_or_sections: Any, language: str = "roman_urdu") -> str:
    if isinstance(message_or_sections, str):
        return message_or_sections

    sections = message_or_sections if isinstance(message_or_sections, list) else []
    entries: list[dict[str, str]] = []
    seen_messages: set[str] = set()

    for section in sections:
        if not isinstance(section, dict):
            continue
        message = (section.get("urdu_message") or "").strip()
        if not message or message in seen_messages:
            continue
        seen_messages.add(message)
        agent = section.get("agent", "")
        urgency = section.get("urgency", "low")
        urgency = URGENCY_ALIASES.get(urgency, urgency)
        title = SECTION_TITLES.get(language, SECTION_TITLES["roman_urdu"]).get(agent, "")
        entries.append({"title": title, "message": message, "urgency": urgency})

    if not entries:
        return ""

    entries.sort(key=lambda item: URGENCY_ORDER.get(item["urgency"], 3))

    if len(entries) == 1 and not entries[0]["title"]:
        return entries[0]["message"]

    blocks: list[str] = []
    for entry in entries:
        if entry["title"]:
            blocks.append(f"{entry['title']}:\n{entry['message']}")
        else:
            blocks.append(entry["message"])

    return "\n\n".join(blocks)

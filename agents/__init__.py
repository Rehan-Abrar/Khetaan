"""Khetaan agent package."""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "CropAgent",
    "FallbackAgent",
    "HelpAgent",
    "MarketAgent",
    "RomanUrduNormalizer",
    "RouterAgent",
    "WeatherAgent",
]

_MODULES = {
    "CropAgent": "agents.crop_agent",
    "FallbackAgent": "agents.fallback_agent",
    "HelpAgent": "agents.help_agent",
    "MarketAgent": "agents.market_agent",
    "RomanUrduNormalizer": "agents.roman_urdu_normalizer",
    "RouterAgent": "agents.router_agent",
    "WeatherAgent": "agents.weather_agent",
}


def __getattr__(name: str):
    module_name = _MODULES.get(name)
    if not module_name:
        raise AttributeError(f"module 'agents' has no attribute {name!r}")

    module = import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value
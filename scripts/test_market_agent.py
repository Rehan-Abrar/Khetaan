"""
Test the market agent fallback path (no Gemini needed).
This simulates what happens when GeminiClient raises RuntimeError
(no API key set), which triggers _fallback_message -> _simple_summary.
"""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Don't set GEMINI_API_KEY so GeminiClient raises RuntimeError
# and the agent uses the fallback formatter
os.environ.pop("GEMINI_API_KEY", None)

import asyncio

# Patch GeminiClient to always raise so we test the fallback path cleanly
import utils.gemini_client as gc
_orig = gc.GeminiClient.__init__
def _raise(self, *a, **kw):
    raise RuntimeError("no key")
gc.GeminiClient.__init__ = _raise

from agents.market_agent import MarketAgent

async def test():
    agent = MarketAgent()

    print("=== All crops (Roman Urdu) ===")
    result = await agent.get_prices(language="roman_urdu")
    print(result["urdu_message"])

    print("\n=== Wheat filter ===")
    result = await agent.get_prices(crop_filter="wheat", language="roman_urdu")
    print(result["urdu_message"])

    print("\n=== English ===")
    result = await agent.get_prices(language="english")
    print(result["urdu_message"])

asyncio.run(test())

"""Test single image diagnosis."""
import sys, asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv()

from agents.crop_agent import CropAgent

async def test():
    agent = CropAgent()
    img = (ROOT / "reference_images" / "wheat_leaf_rust_1.jpg").read_bytes()
    result = await agent.diagnose("test", img, "image/jpeg", "roman_urdu")
    print(f"Disease: {result['disease']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Urgency: {result['urgency']}")
    print(f"Message: {result['urdu_message'][:150]}")

asyncio.run(test())

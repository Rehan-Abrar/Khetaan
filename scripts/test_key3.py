"""Test KEY3 specifically."""
import sys, asyncio, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv()

print(f"KEY3 loaded: {os.getenv('GEMINI_API_KEY3', 'NOT FOUND')[:20]}...")

from agents.crop_agent import CropAgent

async def test():
    agent = CropAgent()
    if agent.client is None:
        print("ERROR: Client is None")
        return
    
    print(f"Client initialized with {len(agent.client.api_keys)} keys")
    print(f"Using key: {agent.client.api_keys[0][:20]}...")
    
    img = (ROOT / "reference_images" / "wheat_leaf_rust_1.jpg").read_bytes()
    result = await agent.diagnose("test", img, "image/jpeg", "roman_urdu")
    print(f"\nDisease: {result['disease']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Urgency: {result['urgency']}")
    print(f"Message: {result['urdu_message'][:150]}")

asyncio.run(test())

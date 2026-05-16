"""Test KEY3 directly with google.genai."""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types

key3 = os.getenv("GEMINI_API_KEY3", "")
print(f"Testing KEY3: {key3[:20]}...")

client = genai.Client(api_key=key3)

img_bytes = Path("reference_images/wheat_leaf_rust_1.jpg").read_bytes()

try:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            "You are a crop disease expert. Analyze this image.",
            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
            'Return JSON only: {"disease": "name", "confidence": 80, "urgency": "high", "urdu_message": "text", "suggestions": []}',
        ],
        config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=512),
    )
    print("SUCCESS!")
    print(response.text[:300])
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

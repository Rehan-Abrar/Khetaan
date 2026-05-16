"""Quick debug script to verify the new google.genai SDK and model work."""
from __future__ import annotations
import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types

api_key = os.getenv("GEMINI_API_KEY", "").strip()
model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
print(f"Key prefix: {api_key[:10]}...")
print(f"Model: {model_name}")

client = genai.Client(api_key=api_key)

img_bytes = (ROOT / "reference_images" / "wheat_leaf_rust_1.jpg").read_bytes()

prompt = 'Return JSON only: {"disease": "name", "confidence": 80, "urgency": "high", "urdu_message": "text", "suggestions": []}'

# Try requested model only
print(f"\nTrying model: {model_name}")
try:
    response = client.models.generate_content(
        model=model_name,
        contents=[
            "You are a crop disease expert. Analyze this image.",
            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
            prompt,
        ],
        config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=512),
    )
    print("SUCCESS")
    print("Response:", response.text[:400])
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
import os

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
model = genai.GenerativeModel(model_name)
img = (ROOT / "reference_images" / "wheat_leaf_rust_1.jpg").read_bytes()

prompt = (
    "You are an expert agronomist. Look at this crop photo carefully. "
    "Identify any disease present. "
    'Reply ONLY with valid JSON, no markdown, no explanation: '
    '{"disease": "name or Healthy", "confidence": "high or medium or low", "description": "what you see"}'
)

resp = model.generate_content([
    prompt,
    {"mime_type": "image/jpeg", "data": img}
])
print(resp.text)
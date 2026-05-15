import sys
from dotenv import load_dotenv
from utils.gemini_client import GeminiClient

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    try:
        client = GeminiClient()
    except Exception as exc:
        print(f"GEMINI_ERROR: {exc}")
        return

    result = client.generate_json([
        "Return JSON only.",
        "Format: {\"status\":\"ok\"}",
    ])
    print(f"GEMINI_RESULT: {result}")

if __name__ == "__main__":
    main()
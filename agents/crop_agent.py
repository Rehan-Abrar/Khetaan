class CropAgent:
    async def diagnose(self, image_bytes: bytes) -> dict:
        return {
            "disease_detected": False,
            "disease_name": "Unknown",
            "confidence": "low",
            "urdu_message": "فصل کی تشخیص کا حصہ ابھی تیار ہو رہا ہے۔",
            "treatment": "",
            "urgency": "کم",
        }

class WeatherAgent:
    async def advise(
        self,
        lat: float,
        lon: float,
        disease_context: str | None = None,
    ) -> dict:
        return {
            "urdu_message": "موسمی مشورہ کا حصہ ابھی تیار ہو رہا ہے۔",
            "urgency": "کم",
        }

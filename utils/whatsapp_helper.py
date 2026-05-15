from utils.urdu_formatter import format_urdu_message


def build_whatsapp_reply(message: str, language: str = "roman_urdu") -> str:
    """Format a reply message before sending via Meta WhatsApp Cloud API."""
    return format_urdu_message(message, language=language)

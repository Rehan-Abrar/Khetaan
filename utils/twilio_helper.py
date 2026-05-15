from utils.urdu_formatter import format_urdu_message


def build_whatsapp_reply(message) -> str:
    return format_urdu_message(message)

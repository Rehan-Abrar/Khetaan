from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response

from orchestrator import Orchestrator
from utils.gemini_client import DEFAULT_MODEL, GeminiClient

load_dotenv()

app = FastAPI(title="Khetaan", version="0.3.0")
orchestrator = Orchestrator()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "khetaan_verify_123")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
META_GRAPH_API_VERSION = os.getenv("WHATSAPP_GRAPH_API_VERSION", "v25.0")


def _messages_url() -> str:
    if not PHONE_NUMBER_ID:
        raise RuntimeError("WHATSAPP_PHONE_NUMBER_ID is not set.")
    return f"https://graph.facebook.com/{META_GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages"


# ── Webhook verification (Meta calls this once to confirm your server) ──
@app.get("/webhook")
async def verify_webhook(request: Request) -> Response:
    params = dict(request.query_params)
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return Response(content=params["hub.challenge"])
    return Response(status_code=403)


# ── Incoming messages ──
@app.post("/webhook")
async def receive_message(request: Request) -> dict:
    body = await request.json()

    try:
        entry = body["entry"][0]["changes"][0]["value"]

        # Ignore status updates (delivered / read receipts)
        if "messages" not in entry:
            return {"status": "ok"}

        msg = entry["messages"][0]
        sender: str = msg["from"]  # farmer's WhatsApp number (E.164)
        msg_type: str = msg["type"]

        message_text = ""
        image_bytes: bytes | None = None
        media_type: str | None = None

        if msg_type == "text":
            message_text = msg["text"]["body"]

        elif msg_type == "image":
            try:
                media_id = msg["image"]["id"]
                image_bytes = await download_media(media_id)
                message_text = msg["image"].get("caption", "")
                media_type = msg["image"].get("mime_type") or "image/jpeg"
            except Exception as exc:
                print(f"Image download failed sender={sender} error={exc}")
                await send_whatsapp_message(
                    sender,
                    "Tasveer process nahi ho saki, meherbani clear photo bhejein.",
                )
                return {"status": "ok"}

        elif msg_type in ("audio", "voice"):
            media_id = msg[msg_type]["id"]
            audio_bytes = await download_media(media_id)
            message_text = await transcribe_audio(audio_bytes)

        print(f"Webhook inbound sender={sender} type={msg_type} text={message_text!r}")

        # Return 200 immediately to prevent Meta retries
        # Process the message in background
        import asyncio
        asyncio.create_task(_process_message(sender, message_text, image_bytes, media_type))

    except Exception as e:
        print(f"Webhook error: {e}")

    return {"status": "ok"}  # always return 200 to Meta


async def _process_message(sender: str, message_text: str, image_bytes: bytes | None, media_type: str | None) -> None:
    """Process message in background to avoid webhook timeout."""
    try:
        reply = await orchestrator.route(
            message=message_text,
            image_bytes=image_bytes,
            sender=sender,
            media_type=media_type,
        )
        print(f"Webhook reply sender={sender} reply={reply!r}")
        await send_whatsapp_message(sender, reply)
    except Exception as e:
        print(f"Background processing error: {e}")


# ── Send reply ──
async def send_whatsapp_message(to: str, text: str) -> None:
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    try:
        messages_url = _messages_url()
    except RuntimeError as exc:
        print(f"Meta send skipped: {exc}")
        return

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(messages_url, headers=headers, json=payload)
        if resp.status_code != 200:
            print(f"Send failed ({resp.status_code}): {resp.text}")


# ── Download media from Meta servers ──
async def download_media(media_id: str) -> bytes:
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    async with httpx.AsyncClient(timeout=20) as client:
        # Step 1: resolve media URL
        url_resp = await client.get(
            f"https://graph.facebook.com/{META_GRAPH_API_VERSION}/{media_id}",
            headers=headers,
        )
        url_resp.raise_for_status()
        media_url: str = url_resp.json()["url"]

        # Step 2: download the actual file
        file_resp = await client.get(media_url, headers=headers)
        file_resp.raise_for_status()
        return file_resp.content


# ── Transcribe audio via Gemini ──
async def transcribe_audio(audio_bytes: bytes) -> str:
    if not GEMINI_API_KEY:
        return ""
    try:
        client = GeminiClient()
        response = client.client.models.generate_content(
            model=client.model_name,
            contents=[
                "Transcribe this voice note into Roman Urdu using Latin letters only. "
                "Do not use Urdu script. Return only the transcribed text.",
                {"mime_type": "audio/ogg", "data": audio_bytes},
            ],
            config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=512),
        )
        return (getattr(response, "text", "") or "").strip()
    except Exception as exc:
        print(f"Audio transcription failed: {exc}")
        return ""


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "project": "Khetaan"}

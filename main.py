from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Response
from twilio.twiml.messaging_response import MessagingResponse

from orchestrator import Orchestrator

load_dotenv()

app = FastAPI(title="Khetaan", version="0.2.0")
orchestrator = Orchestrator()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "project": "Khetaan"}


@app.post("/webhook")
async def webhook(
    Body: str = Form(default=""),
    MediaUrl0: str | None = Form(default=None),
    MediaContentType0: str | None = Form(default=None),
    From: str = Form(default=""),
    To: str = Form(default=""),
) -> Response:
    image_bytes = None
    if MediaUrl0:
        auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(MediaUrl0, auth=auth)
            if response.status_code == 200:
                image_bytes = response.content

    reply = await orchestrator.route(
        message=Body,
        image_bytes=image_bytes,
        sender=From,
        media_type=MediaContentType0,
    )

    twiml = MessagingResponse()
    twiml.message(reply)
    return Response(content=str(twiml), media_type="application/xml")

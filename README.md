# Khetaan 🌾

A multi-agent WhatsApp AI assistant for Pakistani smallholder farmers. Send a photo, voice note, or text in Roman Urdu, Urdu script, or English — Khetaan diagnoses crop diseases, advises on irrigation, and shows live mandi prices. No app install. Works on 3G.

Built for **SDG Halshanas Edition II** — GDGoC BNU × Google for Developers, MVP Track.

---

## The Problem

Pakistan has 8.5M+ smallholder farmers. **30–40% of annual crop yield is lost** — largely preventable — due to delayed disease detection, poor irrigation timing, and price opacity that lets middlemen underpay at market. Most AgriTech solutions require app downloads and technical literacy. Khetaan works inside WhatsApp with zero onboarding.

---

## Architecture

```
Farmer (WhatsApp)
       │
       ▼
Meta Cloud API webhook
       │
       ▼
FastAPI backend
       │
       ▼
  Orchestrator  ─── Gemini intent detection, language detection,
       │              conversation history per phone number
       ├──────────────────────┬──────────────────────┐
       ▼                      ▼                      ▼
  Crop Agent           Weather Agent          Market Agent
  (Gemini 2.5 Flash    (Open-Meteo,           (Punjab AMIS
   multimodal)          free, no key)          cache/scraper)
       │                      │                      │
       └──────────────────────┴──────────────────────┘
                              │
                              ▼
                   Combined Roman Urdu reply
```

### Orchestrator

- Uses Gemini to classify intent — not keyword matching. Handles Roman Urdu, Urdu script, English, and mixed input.
- Routes to one or more agents in parallel based on meaning.
- Maintains per-phone conversation history (up to 10 turns) — remembers city after the farmer mentions it once.

### Crop Agent

- Multimodal diagnosis via Gemini 2.5 Flash. Analyzes the farmer's photo against a disease-specific prompt.
- Target diseases: **Wheat Leaf Rust**, **Cotton Leaf Curl Virus**, **Aphids**.
- Returns: disease name, confidence, urgency, Roman Urdu treatment advice.
- Falls back to text-only symptom analysis when no photo is provided.

### Weather Agent

- Live data from Open-Meteo (free, no API key required).
- Gives irrigation advice based on temperature and rain probability.
- **Cross-agent verification**: if the Crop Agent detects a fungal disease (rust, CLCuV) and rain is forecast ≥40%, the Weather Agent overrides its default irrigation advice — fungal diseases spread faster in moisture, so the combined reply warns the farmer to stop irrigation and improve airflow.

### Market Agent

- Punjab mandi prices for wheat, cotton, rice, and common vegetables across major cities.
- Data sourced from AMIS Pakistan, cached locally. Live scraping is geo-blocked from foreign servers (including Render's US IPs) — the chosen approach is a pre-populated JSON cache with a scheduled local refresh path.

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Backend | Python FastAPI | Async-friendly, fast to prototype |
| WhatsApp | Meta Cloud API | Free tier, no aggressive rate limits |
| AI | Gemini 2.5 Flash (`google-genai` SDK) | Free tier, multimodal, fast |
| Weather | Open-Meteo | Free, no key, accurate for Pakistan |
| Market data | Cached JSON from AMIS Pakistan | Geo-block workaround |
| Deployment | Render (Python 3.12 pinned) | Team familiarity |
| Language output | Roman Urdu (default) / English | Matches real farmer typing patterns |

**Key engineering decisions:**
- Multi-API-key rotation for Gemini to handle free-tier quota limits.
- Image compression before sending to Gemini — large photos caused `RemoteProtocolError` disconnects.
- Language auto-detection: Urdu script → Urdu reply; 2+ English hint words → English reply; otherwise Roman Urdu (the real-world default — farmers type `"pani dena hai"` not `"پانی"`).
- Confidence-based fallback gates only on the `disease` field being empty, not on Gemini's confidence score (which varies between identical calls).

---

## Quickstart

```bash
py -3.12 -m venv venv_new
venv_new\Scripts\activate
cp .env.example .env        # fill in your keys
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

> Use Python 3.12. Python 3.14 breaks `google-generativeai` due to protobuf changes — the project uses the newer `google-genai` SDK to avoid this entirely, but 3.12 is pinned for consistency with the Render deployment.

## Environment Variables

```env
GEMINI_API_KEY=...                   # rotate multiple keys for quota headroom
WHATSAPP_ACCESS_TOKEN=...            # temporary token from Meta developer dashboard
WHATSAPP_PHONE_NUMBER_ID=...         # Meta app → WhatsApp → API Setup
WHATSAPP_VERIFY_TOKEN=...            # your chosen token for webhook verification
WHATSAPP_WABA_ID=...                 # WhatsApp Business Account ID
PORT=8000
```

## Webhook Setup (local dev)

```bash
ngrok http 8000
# Meta app dashboard → WhatsApp → Configuration → Webhook:
# URL:          https://<ngrok-id>.ngrok.io/webhook
# Verify token: <your WHATSAPP_VERIFY_TOKEN>
# Subscribe to: messages
```

## Health Check

```
GET /health → {"status": "ok", "project": "Khetaan"}
```

## Smoke Tests

```bash
# Test the crop diagnosis pipeline locally
python scripts/photo_smoke_test.py
```

Checks wheat rust, cotton leaf curl, aphid, healthy-crop, and blurry-photo paths. Requires a valid Gemini API key and Python 3.12.

---

## What We Debugged (the real build story)

Worth knowing for a technical review — every item below is a real production issue, not a hypothetical:

1. **Python 3.14 incompatibility** — `google-generativeai` (old SDK) doesn't support Python 3.14's protobuf changes. Fixed by pinning Python 3.12 in `render.yaml` and migrating to the `google-genai` SDK.
2. **Leaked API key** — an exposed Gemini key was auto-revoked by Google. Rotated to a fresh key, added `.env` to `.gitignore`.
3. **Payload size errors** — sending full-resolution reference images (600KB+) to Gemini caused `RemoteProtocolError` disconnects. Fixed with image compression before API calls.
4. **Over-aggressive fallback** — the confidence-based rejection was randomly refusing correct diagnoses because Gemini's confidence score varies between identical calls. Fixed by gating only on the `disease` field being empty/unclear.
5. **Mandi scraper geo-blocked** — AMIS Pakistan blocks foreign IPs (Render's US servers). Solved by pre-scraping real data once and serving from a committed JSON cache.
6. **Webhook duplicate messages** — Meta retries webhooks that don't respond fast enough. Needs background task processing (in progress).

---

## Voice Conversation Pipeline 🎙️

Khetaan supports voice note conversation, allowing farmers to send audio notes and receive both a text response and a spoken voice note reply.

- **Speech-to-Text (STT)**: Powered by `faster-whisper` (running the "small" model locally on the CPU). It auto-detects the spoken language (Urdu, English, Punjabi, etc.) and returns plain text.
- **Text-to-Speech (TTS)**: Powered by `edge-tts` (completely free). It automatically normalizes Roman Urdu responses to standard Urdu script using Gemini, enabling natural-sounding voice replies in a native accent (`ur-PK-UzmaNeural`).
- **Audio Conversion**: Uses `ffmpeg` to transcode incoming voice files into WAV for Whisper and converts synthesised MP3 files into WhatsApp-compatible OGG/Opus voice messages.

### Local Development Setup:
1. Ensure `ffmpeg` is installed and added to your system `PATH`, or place the `ffmpeg.exe` binary in a `bin/` directory in the project root.
2. The Whisper model is pre-loaded on application startup.

### Render Deployment Notes:
- Render's native Python environment includes `ffmpeg` pre-installed in the system PATH.
- The model is cached automatically on the ephemeral disk upon first startup.

---

## Known Limitations

- WhatsApp sandbox requires manual number whitelisting — production needs Meta business verification.
- Mandi prices are cached, not streaming live (geo-block constraint; documented workaround path exists via scheduled local refresh).
- Whisper STT and Edge-TTS processing on Render's free tier CPU can take between 5–15 seconds per voice message.
- Render free tier sleeps after inactivity — first message after idle takes ~50 seconds.
- Crop diagnosis is prompt-engineered, not a fine-tuned model — works reliably for the 3 target diseases, not exhaustive across all crops and conditions.

---

## SDG Alignment

| Goal | How |
|---|---|
| SDG 2 — Zero Hunger | Early disease detection reduces preventable crop loss |
| SDG 1 — No Poverty | Market price transparency protects farmer income from middleman exploitation |
| SDG 8 — Decent Work | Supports livelihood stability for Pakistan's largest informal labor sector |
| SDG 9 — Innovation | Reusable AgriTech infrastructure extensible across regions and crops |

---

## Scalability Path

The agent separation was designed to absorb growth without a rewrite:

- **Render free tier → Cloud Run**: scales to zero, pays per request.
- **JSON cache → scheduled background job**: writes to a proper DB, removes the manual refresh dependency.
- **Meta sandbox → verified business number**: unlocks production WhatsApp access.
- **3 diseases → broader crop coverage**: extend the Crop Agent prompt or swap in a fine-tuned vision model without touching other agents.

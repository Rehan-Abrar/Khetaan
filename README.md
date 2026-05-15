# Khetaan

Khetaan is a WhatsApp-first assistant for Pakistani smallholder farmers — built on Meta WhatsApp Cloud API and Google Gemini.

A farmer sends a photo or voice note in Urdu via WhatsApp. The system diagnoses crop disease, checks weather, fetches live mandi prices, and replies in Urdu — all within one message thread. Zero app install. Works on 3G.

## Stack

| Layer | Choice |
|---|---|
| Backend | Python FastAPI |
| WhatsApp | Meta WhatsApp Cloud API |
| AI | Gemini 2.5 Flash (Google AI Studio) |
| Weather | Open-Meteo (free, no key) |
| Mandi prices | Punjab AMIS scraper |
| Deployment | Render |

## Quickstart

```bash
py -3.12 -m venv venv_new
venv_new\Scripts\activate
cp .env.example .env      # fill in your keys
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Use Python 3.12 for local development. Python 3.14 breaks `google-generativeai` in this project.

## Environment variables

```env
GEMINI_API_KEY=...
WHATSAPP_ACCESS_TOKEN=...        # temporary token from Meta developer dashboard
WHATSAPP_PHONE_NUMBER_ID=...     # from Meta app → WhatsApp → API Setup
WHATSAPP_VERIFY_TOKEN=...        # your chosen verify token for webhook setup
WHATSAPP_WABA_ID=...             # WhatsApp Business Account ID
PORT=8000
```

## Webhook setup (local dev)

```bash
ngrok http 8000
# Then in Meta app dashboard → WhatsApp → Configuration → Webhook:
# URL:          https://<ngrok-id>.ngrok.io/webhook
# Verify token: khetaan_verify_123
# Subscribe to: messages
```

## Health check

```
GET /health → {"status": "ok", "project": "Khetaan"}
```

## Photo smoke test

```bash
python scripts/photo_smoke_test.py
```

This checks the wheat rust, cotton leaf curl, aphid, healthy, and blurry-photo paths locally. It requires a valid Gemini API key and a Python 3.12 runtime.

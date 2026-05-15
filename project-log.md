# Project Log

## 2026-05-15

- Created the initial Khetaan scaffold.
- Added the FastAPI health endpoint entrypoint.
- Added the agent, scraper, and utility package structure.
- Added deployment, environment, and dependency placeholders.
- Added the Twilio WhatsApp `/webhook` route for inbound sandbox testing.
- Relaxed the Pillow pin so dependencies install on Python 3.14.
- Updated the build plan to use Gemini-based intent detection and voice-note transcription.
- Replaced the hard-coded Gemini key in `.env.example` with a placeholder.
- Updated intent routing prompt and fallback matching to better handle Roman Urdu and mixed text.
- Guarded the Twilio webhook media download to avoid treating non-image media as images.
- Added language-aware responses (Roman Urdu or English only), conversation history, and voice-note transcription.
- Migrated from Twilio to Meta WhatsApp Cloud API — removed `twilio` dependency, replaced Twilio sandbox webhook with Meta Cloud API webhook (GET verify + POST receive), updated env vars (WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN, WHATSAPP_WABA_ID), renamed `twilio_helper.py` → `whatsapp_helper.py`, updated `requirements.txt`, `render.yaml`, `.env`, `.env.example`, `plan.md`, and `README.md` throughout.
- Added the Meta phone number ID to the live `.env` and switched the runtime token to a temporary dashboard token so outbound WhatsApp sends can succeed again.
- Restarted the app with the updated Meta env and validated the webhook path locally; the send call now reaches Meta and only fails on a synthetic test recipient that is not in the allow list.
- Confirmed the manual Meta Cloud API send works with the working v25.0 endpoint and temporary access token; aligned the app default Graph API version and deployment config to v25.0.
- Fixed weather routing for Roman Urdu queries like `barish` / `baarish` so `Lahore mein barish hai ya nahi?` reaches `weather_agent` instead of the fallback help reply; reloaded the live uvicorn process to pick up the updated orchestrator.
- Added lightweight webhook tracing in `main.py` to print incoming WhatsApp sender/type/text and the generated reply so live Meta webhook traffic can be debugged without changing behavior.
- Made weather replies data-driven and city-aware: the weather agent now prints the resolved city, live temperature, and 24-hour rain chance instead of the previous generic "Mausam theek hai" wording.
- Replaced the crop diagnosis dependency on Gemini with a local Pillow-based reference-image classifier so clear wheat rust, cotton leaf curl, and aphid photos can be recognized even when the Gemini API key is unavailable; added blur/unsupported-image fallbacks and farmer-safe treatment advice.
- Wired the Meta webhook image branch to pass the uploaded mime type into the crop agent and return a graceful clear-photo reply when an image download fails.
- Added a post-diagnosis weather cross-check so fungal crop risks can pick up a rain warning when the farmer has already shared a location.
- Added a reusable `scripts/photo_smoke_test.py` runner to validate the disease, healthy, and blurry-photo paths without retyping the ad-hoc test command.
- Reverted the crop agent back to Gemini multimodal diagnosis, removed the Pillow classifier, and confirmed the repo now needs Python 3.12 for `google-generativeai` to import cleanly.
- Created a fresh `venv_new` with Python 3.12 and installed the project dependencies successfully.
- Retested Gemini access under Python 3.12: the runtime is correct, but the current Gemini API key is rejected by Google as leaked, so a fresh key is still required before model calls can succeed.

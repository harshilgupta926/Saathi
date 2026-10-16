# Saathi

**Your voice. Your language. Your companion.**

Saathi is a voice-first, multilingual assistance platform designed to make useful information and service workflows accessible through simple conversations. The project is built around one principle: field-ready workflows over disconnected AI demos.

## Current status

The non-Supabase implementation is now consolidated into a production-shaped prototype:

- responsive landing page and operator command center
- deterministic Hindi/Hinglish intent routing and 120-case synthetic benchmark
- source provenance and demo/live data labelling
- Open-Meteo weather adapter
- configurable government OGD/AGMARKNET mandi adapter
- local Vosk Hindi speech recognition and eSpeak NG speech synthesis as the API-key-free default, plus optional provider-gated Sarvam STT/TTS
- executable Exotel AgentStream WebSocket endpoint with bounded-turn Sarvam phone speech adapter plus optional Sarvam Realtime STT/streaming TTS transport
- telephony HMAC/idempotency contracts
- rate limiting, correlation IDs, baseline API security headers and capability-aware readiness
- current Sarvam Document AI adapter for Digitise/Extract jobs (optional hosted integration)
- local Tesseract OCR endpoint for bounded Hindi/English image uploads, with confidence metadata and human-review flags
- consent and human-escalation UI
- automated backend/frontend CI and dependency audits

The operator demo intentionally uses labelled simulated data when live credentials are absent. Persistent Supabase memory, durable webhook storage, low-latency realtime phone transport, human case persistence and authorized government application submission remain separate integration/deployment gates.

**Product demo:** run the frontend and backend, then open `/dashboard`. If Sarvam is not configured, browser-native speech recognition/synthesis is used and visibly treated as local demo voice rather than live provider voice.

**Streamlit demo:** for the standalone judge-friendly demo, deploy `streamlit_app/app.py` to Streamlit Community Cloud. See `docs/STREAMLIT_DEPLOY.md` for the exact setup and supported secrets.

**Render API:** the root `Dockerfile` deploys the current FastAPI backend as a Docker web service. Follow `docs/RENDER_DEPLOY.md`; leave Render's Root Directory blank and set Dockerfile Path to `./Dockerfile`.

**Vercel + Supabase connection:** deploy the Next.js app with `frontend/` as the Vercel Root Directory, set `BACKEND_API_URL` to the public FastAPI origin, and configure the Supabase server-side secret on the API service. Follow `docs/VERCEL_SUPABASE_CONNECT.md`.

## API-key-free local development

The backend defaults to local Ollama tool selection (`qwen2.5:7b`, Apache-2.0 model family variant) and does not need a hosted LLM key for that path. Install Ollama, run `ollama pull qwen2.5:7b`, set `LLM_PROVIDER=ollama` and `OLLAMA_BASE_URL=http://127.0.0.1:11434`, and set `DEMO_MODE=false` to activate local reasoning. The 7B model has a higher RAM/latency requirement than the previously listed 3B variant; confirm hardware suitability before deployment. `DEMO_MODE=true` deliberately remains deterministic and network-free for CI and synthetic demo data. See [the open-source-first architecture and remaining offline gates](docs/OPEN_SOURCE_FIRST.md). Local LLM reasoning is optional; deterministic routing remains available if Ollama is offline. The backend includes `POST /api/v1/documents/ocr` for keyless local image OCR when Tesseract is installed; it does not yet support PDFs or have a real-image Hindi accuracy benchmark. Backend audio turns use the local Vosk Hindi model and eSpeak NG by default, with no hosted fallback; download the Apache-2.0 Vosk Hindi model and mount it at `VOSK_MODEL_PATH` as described in `docs/LOCAL_DEMO.md`. Real Hindi/Hinglish/Haryanvi accuracy and latency benchmarks remain outstanding.

## Product direction

1. Voice-first access through phone or browser.
2. Hindi-first, with an adapter architecture for Indian languages and dialects.
3. Specialist workflows for schemes, farming, documents, and tasks.
4. Consent-based household memory and unfinished-task continuity.
5. Proactive reminders/callbacks only after explicit outbound consent.
6. Human volunteer fallback when automation is uncertain or requested.
7. Source-backed factual answers; the LLM is not the source of truth.

## Repository

- `frontend/` — Next.js + React interface and operator control room
- `backend/` — FastAPI API, agent orchestration and provider boundaries
- `docs/` — architecture, API contracts, build plan, voice contract, evaluation and release gates
- `.github/workflows/` — backend tests, frontend checks/build and dependency audits

## Development

Requirements: Node.js 24+, Python 3.11+.

Frontend: `cd frontend && npm install && npm run dev`

Backend: `cd backend && python -m venv .venv && pip install -r requirements.txt && pytest -q && uvicorn app.main:app --reload`

Fast demo stack: `docker compose up --build`. Full local AI stack (Ollama model pull, no hosted AI key) requires a random internal API token first: `export SAATHI_API_AUTH_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"` then `docker compose -f docker-compose.yml -f docker-compose.local-ai.yml up --build`. See `docs/LOCAL_DEMO.md` for setup and resource requirements.

Never commit `.env` files or secrets. Start from the provided `.env.example` files.

## Engineering rules

- Do not hard-code provider secrets.
- Do not fabricate eligibility, prices, weather, deadlines, or application status.
- Keep external providers behind replaceable adapters.
- Keep household data isolated with RLS when persistence is enabled.
- Use synthetic data for development and demos.
- Require explicit consent before storing memory or making outbound calls.
- Treat healthcare as informational/navigation support in the MVP.
- Do not merge failing required checks.
- Every factual tool result must carry provenance and retrieval time.
- Demo/simulated data must be explicitly labelled.
- A capability is only called live after its real provider path has been exercised.

## Release roadmap

See `docs/OWNER_ACTIONS.md` for the short list of API keys, manual account setup, and speech evaluation work; `docs/BUILD_PLAN.md` for release gates; and `docs/DEPLOYMENT_RUNBOOK.md` for deployment, smoke tests, provider configuration, and rollback. The repository is deployable as a demo, but it is not yet honest to call every capability production-ready: live provider tests, real phone-call proof, authenticated household persistence, durable webhooks, and shared rate limiting remain release gates.

## Hackathon

The project is being prepared for JAI 2026 and Tech Eximius 2.0. Submission claims will match functionality actually demonstrated by the submitted build.

## Real voice, data and evaluation

See:

- `docs/VOICE_RUNTIME.md`
- `docs/REAL_DATA.md`
- `docs/EVALUATION.md`
- `docs/JAI_SUBMISSION_CHECKLIST.md`

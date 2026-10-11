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
- provider-gated Sarvam browser STT/TTS
- executable Exotel AgentStream WebSocket endpoint with bounded-turn Sarvam phone speech adapter plus optional Sarvam Realtime STT/streaming TTS transport
- telephony HMAC/idempotency contracts
- rate limiting, correlation IDs, baseline API security headers and capability-aware readiness
- current Sarvam Document AI adapter for Digitise/Extract jobs
- consent and human-escalation UI
- automated backend/frontend CI and dependency audits

The operator demo intentionally uses labelled simulated data when live credentials are absent. Persistent Supabase memory, durable webhook storage, low-latency realtime phone transport, human case persistence and authorized government application submission remain separate integration/deployment gates.

**Operator demo:** run the frontend and open `/dashboard`.

**Streamlit demo:** for the standalone judge-friendly demo, deploy `streamlit_app/app.py` to Streamlit Community Cloud. See `docs/STREAMLIT_DEPLOY.md` for the exact setup and supported secrets.

**Render API:** the root `Dockerfile` deploys the current FastAPI backend as a Docker web service. Follow `docs/RENDER_DEPLOY.md`; leave Render's Root Directory blank and set Dockerfile Path to `./Dockerfile`.

**Vercel + Supabase connection:** deploy the Next.js app with `frontend/` as the Vercel Root Directory, set `BACKEND_API_URL` to the public FastAPI origin, and configure the Supabase server-side secret on the API service. Follow `docs/VERCEL_SUPABASE_CONNECT.md`.

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

See `docs/BUILD_PLAN.md` for the current gates and `docs/DEPLOYMENT_RUNBOOK.md` for staged Vercel/Render deployment, smoke tests, provider configuration, and rollback. The repository is deployable as a demo, but it is not yet honest to call every capability production-ready: live provider tests, real phone-call proof, authenticated household persistence, durable webhooks, and shared rate limiting remain release gates.

## Hackathon

The project is being prepared for JAI 2026 and Tech Eximius 2.0. Submission claims will match functionality actually demonstrated by the submitted build.

## Real voice, data and evaluation

See:

- `docs/VOICE_RUNTIME.md`
- `docs/REAL_DATA.md`
- `docs/EVALUATION.md`
- `docs/JAI_SUBMISSION_CHECKLIST.md`

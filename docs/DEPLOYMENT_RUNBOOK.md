# Deployment Runbook

Deploy Saathi in demo-safe mode first. A successful build does not prove that live providers, persistence, or telephony work.

## Architecture

- Frontend: Vercel, root directory `frontend/`.
- API: Render Blueprint from `render.yaml`.
- Database: optional; do not enable persistence until the intended Supabase project, schema, Auth, RLS, and isolation tests are verified.
- Local demo: see [LOCAL_DEMO.md](LOCAL_DEMO.md).

## Render API

1. Create the Blueprint from `kaustubhdua/Saathi`; keep the service's Dockerfile/root settings consistent with `render.yaml`.
2. Set `CORS_ORIGINS` to the exact Vercel origin.
3. Set `API_AUTH_TOKEN` to a strong random secret of at least 32 characters.
4. Set `DEMO_MODE=true` for the first deployment.
5. Set `SUPABASE_URL` and Supabase keys only after confirming the intended project and its schema. Do not use a stale URL from an example file.
6. Verify `/health/live` and `/health/ready`.

## Vercel frontend

1. Set Root Directory to `frontend`.
2. Set server-side `BACKEND_API_URL` to the Render HTTPS origin, without a trailing slash.
3. Set server-side `SAATHI_API_AUTH_TOKEN` to the same value as Render's `API_AUTH_TOKEN`.
4. Deploy and test the landing page, dashboard, same-origin `/backend/*` proxy, mobile layout, and capability labels.

Never put server credentials in `NEXT_PUBLIC_*`, source files, client bundles, or Git history.

## Enable only the capabilities you will demonstrate

- Weather: no API key; verify live Open-Meteo output and source/retrieval time.
- Mandi prices: `MANDI_API_KEY` and the verified `MANDI_RESOURCE_ID`; test commodity, location, market date, unit, and source.
- Browser voice: `SARVAM_API_KEY`; test real microphone audio through transcription, tool routing, grounded answer, and Hindi audio playback.
- LLM reasoning: `GEMINI_API_KEY` only if the chosen orchestration path needs it. Deterministic routing should remain available.
- Phone AI: Exotel credentials, public WSS stream URL, public HTTPS callback URL, webhook secret, call token, and successful provider-specific callback-authentication tests. Keep `TELEPHONY_CALLBACK_SIGNATURE_VERIFIED=false` until the actual provider/gateway signature contract is proven. Do not guess that Exotel sends the custom Saathi HMAC header.
- Shared production rate limiting: provision Upstash Redis and set both `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` on Vercel; configure the trusted client-IP header according to the host's documented proxy behavior.
- Persistence: only set Supabase values after the correct project is active and Auth/JWT, migrations, RLS, and cross-household isolation are verified.

Keep `DEMO_MODE=true` until the relevant live path passes. Do not enable phone calls or persistence just to make readiness appear green.

## Release checks

From the repository root:

```bash
cd backend
python -m venv .venv
# Activate the environment, then:
pip install -r requirements.txt
pytest -q
```

In another terminal:

```bash
cd frontend
npm ci
npm run lint
npx tsc --noEmit
npm run build
```

The frontend lockfile is committed; use `npm ci` for reproducible installs. CI is not a substitute for testing the deployed URLs and live provider paths.

## Do not call it production-ready until

- CI passes on the exact release commit.
- Hosted frontend-to-API proxy and authentication work.
- Live weather and mandi results show correct provenance and observation dates.
- Real Sarvam voice completes STT → tool → Hindi TTS.
- If phone AI is advertised, a real Exotel call completes the WSS audio round trip and interruption test.
- Household identity is verified server-side and RLS isolation tests pass before storing household data.
- Webhook replay protection survives restarts; rate limiting is shared across instances.
- Privacy notice, consent withdrawal, retention, and deletion match actual behavior.
- The exact deployed commit and smoke-test evidence are recorded.

## Rollback

If smoke tests fail, roll back to the last known-good deployment, verify readiness, and repeat the smoke test. Change one provider/configuration at a time while diagnosing failures.


## Household authentication and consent — keep disabled until accepted

- Household OTP/PIN/session routes and memory/task endpoints are candidate code only. Do not enable household persistence or advertise personalisation until the required server-side secrets, active isolated Saathi database, reviewed migrations, authenticated identity-to-household mapping, consent revocation and two-household isolation tests pass.
- New households must default memory and outbound-call consent to off. PIN/session controls must be rate-limited and server-side secrets must never be exposed through `NEXT_PUBLIC_*` variables.
- The household membership SQL remains in `docs/proposed-migrations/` and is not approved for application. Do not apply it to the shared Nihdhoom project; first reconcile migration history and use an authorized isolated test database.
- Reminder delivery, automatic follow-up calls, and volunteer assignment remain disabled until durable scheduling, atomic claims, retries, consent-revocation race tests, idempotency and end-to-end delivery are independently accepted.

# Render deployment — Saathi API

This deploys the **FastAPI backend** as a Docker web service. It does not deploy the Next.js frontend or the Streamlit judge demo.

## Repository and source

The maintained repository is [kaustubhdua/Saathi](https://github.com/kaustubhdua/Saathi), branch `main`.

**Repository mismatch warning:** the Render screenshots supplied during setup show `harshilgupta926/Saathi`. Commits to `kaustubhdua/Saathi` do not update that repository. Connect Render to the maintained repository, or merge/copy the changes into the repository Render actually uses before deploying.

## Recommended setup

Use Render's Blueprint flow with the root `render.yaml`, or create a Docker web service manually:

| Field | Value |
|---|---|
| Name | `saathi-api` |
| Runtime | Docker |
| Branch | `main` |
| Root Directory | **Leave blank** |
| Dockerfile Path | `./Dockerfile` |
| Docker Build Context Directory | `.` if shown |
| Health Check Path | `/health/ready` |

Do not enter `backend/app/` as the Root Directory. The root Dockerfile copies `backend/requirements.txt` and `backend/app` into the image. The backend-local Dockerfile is retained for deployments that deliberately set Root Directory to `backend`; if using that alternative, set Dockerfile Path to `./Dockerfile` and build context to `backend`.

The container binds to Render's `PORT` environment variable, falling back to 8000 for local use.

## Initial environment

The Blueprint sets `APP_ENV=production` and `DEMO_MODE=true`. Add `CORS_ORIGINS` as the exact frontend origin(s), comma-separated. Leave provider secrets unset until you are ready to test them.

Configure Supabase only after applying and reviewing the migration in `supabase/migrations`. Use the backend-only secret key; never expose it in the frontend or commit it to Git. Browser roles should not receive table privileges.

For live provider tests, add the needed `GEMINI_API_KEY`, `SARVAM_API_KEY`, and/or `MANDI_API_KEY`. The mandi resource ID is prefilled with the known AGMARKNET resource identifier. Set `DEMO_MODE=false` only after confirming the corresponding live provider path, data freshness, error handling and provenance.

For Exotel, configure account credentials, a public `wss://` stream URL, webhook secret and call API token only after validating the deployed WebSocket and exact provider signature contract. Never trigger outbound calls without persisted consent, quiet-hour checks, atomic job claiming, idempotency and retry limits.

## What deployment does and does not mean

A successful container build means the API starts; it does not mean every product feature is production-ready. The current code includes deterministic intent handling, weather/mandi adapters, Sarvam voice adapters, Exotel streaming paths, consent/callback policy primitives, and a Supabase migration foundation. Persistent repositories are not yet wired into the request paths, and the durable callback dispatcher, complete volunteer case-management workflow, WhatsApp intake/delivery, verified MyScheme retrieval, and end-to-end production provider tests remain release gates.

For the standalone judge demo, use Streamlit Community Cloud with `streamlit_app/app.py` as documented in `docs/STREAMLIT_DEPLOY.md`.

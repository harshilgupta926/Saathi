# Deployment Runbook

This is the supported first deployment path for Saathi. It deliberately starts in demo-safe mode and enables live providers only after each provider has been tested. A successful cloud build is not evidence that live voice, mandi data, persistence, or telephony works.

## Recommended architecture

- **Frontend:** Vercel, from the `frontend/` directory.
- **API:** Render, from the repository's `render.yaml` blueprint (FastAPI/Docker).
- **Database:** Supabase is optional for the current demo; do not claim persistent memory until the Saathi schema is applied and tenant-isolation tests pass.
- **Fastest judge demo:** Streamlit Community Cloud using `streamlit_app/app.py`; this is a separate demo shell, not the Next.js production frontend.

## 1. Deploy the API on Render

1. Push/merge the release branch after CI passes.
2. In Render, create a Blueprint from `kaustubhdua/Saathi` and select the intended branch.
3. Confirm the service root is `backend`, runtime is Docker, and readiness path is `/health/ready`.
4. Keep `DEMO_MODE=true` for the first deploy. This is intentional: a deploy with missing credentials must not imply that external data is live.
5. Set `CORS_ORIGINS` to the exact frontend origin, for example `https://your-app.vercel.app` (no trailing slash; comma-separate additional trusted origins only).
6. Deploy and verify:
   - `/health/live` returns `{"status":"alive"}`
   - `/health/ready` returns a capability map
   - `/api/v1/agent` returns a clearly labelled demo response while demo mode is on.
7. Save the public HTTPS API URL.

Do not set real API keys in GitHub files, commit history, or client-side `NEXT_PUBLIC_*` variables.

## 2. Deploy the Next.js frontend on Vercel

1. Import `kaustubhdua/Saathi` into Vercel.
2. Set the project root directory to `frontend`.
3. Use the Node version specified by the repository README/runtime requirements.
4. Add `NEXT_PUBLIC_API_URL` with the Render API origin, e.g. `https://your-api.onrender.com` (no trailing slash).
5. Deploy. Add the final Vercel origin to Render's `CORS_ORIGINS`, then redeploy the API if changed.
6. Open the deployed site and test the landing page, dashboard, a text request, mobile layout, and the provider/capability labels.

The public browser variable `NEXT_PUBLIC_API_URL` is an endpoint, not a secret. Provider credentials must remain server-side.

## 3. Configure live providers one at a time

Keep demo mode on until you have set the appropriate server-side credentials and successfully exercised each path.

- **Weather:** Open-Meteo is used by the backend; verify a live request and inspect source/retrieval provenance.
- **Mandi:** set `MANDI_API_KEY` and the confirmed `MANDI_RESOURCE_ID`; test commodity, district, market, observation date, price unit, and source. A retrieval timestamp is not the observation date.
- **Browser voice:** set `SARVAM_API_KEY`; test real microphone capture, transcription, tool result, and returned audio. Record latency and provider errors.
- **Reasoning model:** set `GEMINI_API_KEY` only if the selected orchestration path needs it; the deterministic routing baseline should remain available.
- **Phone calls:** configure Exotel only after the API is deployed on public HTTPS/WSS and the complete call has been tested. Required values include account SID, API key/token, virtual number, stream URL, webhook secret, and a strong call API token. Do not expose call credentials to the browser.
- **Supabase:** leave persistence disabled until migrations, Auth/JWT verification, row-level security, and cross-household tests are complete.

After a provider is tested, turn `DEMO_MODE=false` only when the enabled capability paths are ready for the audience. Verify that unavailable providers fail honestly rather than returning demo values as live facts.

## 4. Release smoke test

Run locally before release:

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Then:

```bash
cd frontend
npm install
npm run lint
npx tsc --noEmit
npm run build
```

The repository currently does not include `frontend/package-lock.json`, so the current workflow uses `npm install` rather than `npm ci`. For reproducible production builds, generate and commit a reviewed lockfile, then switch CI and this runbook to `npm ci`. If a command fails, fix the failure before calling the release ready. The hosted provider tests still need to be run against the actual deployed URLs.

## 5. Do not announce production readiness until these gates pass

- [ ] CI is green on the exact commit to deploy.
- [ ] The hosted frontend can reach the hosted API with the expected CORS policy.
- [ ] Live weather and live mandi queries return correct provenance and dates.
- [ ] Real browser voice completes STT → specialist tool → Hindi TTS.
- [ ] If phone AI is claimed, a real Exotel call completes the WSS audio round trip and interruption test.
- [ ] Authenticated user identity is verified server-side before storing or retrieving household data.
- [ ] Supabase RLS and cross-household tests pass before persistence is enabled.
- [ ] Webhook replay/idempotency survives process restarts before it is called durable.
- [ ] Rate limiting is shared across instances before multi-instance production claims.
- [ ] Privacy notice, consent withdrawal, retention, and deletion behavior match actual data handling.
- [ ] The exact deployed commit and smoke-test evidence are recorded.

## Rollback

If the deployed build fails its smoke test, roll back to the last known-good deployment in the hosting provider, verify `/health/ready`, and repeat the smoke test. Do not change multiple providers or credentials at once while diagnosing a failure.

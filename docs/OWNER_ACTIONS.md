# Owner Actions — Saathi

This is the short list of tasks that require the project owner or access to external provider accounts. Do not fill every key: configure only the features you will demonstrate.

## 1. Required for a safe hosted demo

- [ ] Deploy the API from `render.yaml`; keep `DEMO_MODE=true`.
- [ ] Deploy the frontend on Vercel with Root Directory `frontend`.
- [ ] Set Vercel `BACKEND_API_URL` to the Render HTTPS origin.
- [ ] Generate one strong random secret (at least 32 characters). Set it as Render `API_AUTH_TOKEN` and Vercel `SAATHI_API_AUTH_TOKEN`.
- [ ] Set Render `CORS_ORIGINS` to the exact Vercel origin.
- [ ] Test the deployed landing page, dashboard, API proxy, readiness endpoint, and mobile layout.

## 2. Provider credentials — only for the feature you need

| Feature | Manual values | Required owner action |
|---|---|---|
| Weather | No key | Test a live location-specific request and verify source, units, and observation/forecast time. |
| Government mandi prices | `MANDI_API_KEY`, verified `MANDI_RESOURCE_ID` | Obtain/confirm the data.gov.in key and validate commodity, market, district, price unit, and observation date. |
| Offline Hindi browser voice | No hosted API key; `VOSK_MODEL_PATH` plus local `ffmpeg`/`espeak-ng` binaries | Download the official Apache-2.0 Vosk small Hindi model, mount it at the configured path, and test real microphone audio through transcription, answer generation, and Hindi playback. Hindi/Hinglish/Haryanvi benchmark evidence is still required. |
| Local document OCR | No hosted API key; Tesseract installed in Docker image | Test representative Hindi/English cards/forms, record extraction accuracy, review confidence thresholds, and keep PDF support marked unavailable until implemented. |
| Optional hosted Hindi voice | `SARVAM_API_KEY` | Only if explicitly choosing `SPEECH_PROVIDER=sarvam`; keep it server-side and test a real microphone round trip. Never rely on silent fallback. |
| Local LLM reasoning | No hosted API key; `docker-compose.local-ai.yml` | Run the full local Compose override, allow the Qwen2.5 7B model download (several GB), and measure real tool selection/latency on suitable hardware. |
| Optional hosted LLM | `GEMINI_API_KEY` (optional) | Only if explicitly choosing the Gemini path. Keep the key server-side and do not make deterministic routing depend on it. |
| Alternative speech | `BHASHINI_USER_ID`, `BHASHINI_API_KEY`, STT/TTS endpoints (optional) | Configure only if choosing Bhashini instead of Sarvam. |
| Shared frontend rate limit | Vercel `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`, and documented trusted-IP-header setting | Create an Upstash Redis database and configure it in Vercel before production traffic. |
| Persistent household data | `SUPABASE_URL`, publishable key, server-side secret key | First confirm the intended project is active and its migrations, Auth/JWT verification, RLS, and cross-household tests pass. Keep persistence off until then. |
| Phone calls | Exotel API key/token, account SID, virtual number, public WSS stream URL, HTTPS callback URL, webhook secret, call token, stream token | Create/configure Exotel and run a sandbox call. Prove the callback signature/authentication contract before setting `TELEPHONY_CALLBACK_SIGNATURE_VERIFIED=true`. |

Never put secrets in GitHub, browser-visible `NEXT_PUBLIC_*` variables, screenshots, demo videos, or logs. Do not enable phone calls or persistence simply to make readiness look green.

## 3. Training and evaluation

**Do not fine-tune or train a custom model yet.** The immediate need is evaluation data and evidence, not model training. A custom model would add cost and maintenance before we know which errors the current deterministic routing and provider models make.

Owner/team work:
1. Write 300–500 consent-safe, synthetic Hindi/Hinglish utterances across schemes, weather, mandi, documents, reminders, and human escalation. Add noisy/ambiguous examples and common misspellings.
2. For each example, label expected intent, entities, correct tool, whether the answer must refuse/escalate, and required source.
3. Add a separately reviewed set of Haryanvi-accented speech examples before claiming Haryanvi support. Do not use real personal data without explicit lawful consent and a retention/deletion plan.
4. Test real speech audio, not only text prompts. Measure word error rate (WER), intent accuracy, entity accuracy, tool-selection accuracy, grounded-answer correctness, escalation precision/recall, and end-to-end latency (p50/p95).
5. Review failures with a human, add regression cases, and rerun the same versioned benchmark after each change. Never tune on the final held-out test set.
6. Only consider fine-tuning if a stable, repeated error class remains after prompt/routing/data fixes and a representative, permissioned dataset exists.

## 4. Must be fixed/verified by engineering before a production claim

- [ ] Confirm the intended Supabase project. Example configuration previously contained a hardcoded project URL; examples now leave it blank to prevent accidentally connecting to the wrong project.
- [ ] Run backend tests, frontend lint, TypeScript, build, and dependency audit on the exact commit.
- [ ] Verify deployed frontend-to-API authentication and rate limiting.
- [ ] Capture live weather and mandi results with provenance.
- [ ] Verify Sarvam STT → routing/tool → Hindi TTS with a real key.
- [ ] For phone AI, prove a real Exotel WSS call and callback authenticity; otherwise do not advertise it as live.
- [ ] Before storing household data, verify server-side identity, RLS, isolation, consent withdrawal, retention, and deletion.
- [ ] Record deployed commit SHA and redacted test evidence.

## 5. Current blocker

GitHub issue [#27](https://github.com/kaustubhdua/Saathi/issues/27) reports that the dedicated Saathi Supabase project was inactive and could not be restored because the organization had reached its active-project limit. Confirm the actual target project before entering credentials or enabling persistence. Do not pause/delete another project without an explicit owner decision.

## 6. Release commands

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

```bash
cd frontend
npm ci
npm run lint
npx tsc --noEmit
npm run build
```

Use the repository [Deployment Runbook](DEPLOYMENT_RUNBOOK.md) for deployment details and [Provider Verification](PROVIDER_VERIFICATION.md) for provider-specific evidence.

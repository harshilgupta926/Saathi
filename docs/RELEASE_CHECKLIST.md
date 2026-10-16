# Saathi Release Checklist

This is an evidence gate, not a declaration of completion. Mark an item complete only when the exact candidate commit and target environment have reproducible evidence.

## Current candidate status (2026-10-16)

- [x] Consolidated auth/consent/task/explicit-memory UI and API code is on PR #68.
- [x] Accessible 404, route/global error recovery and dashboard noindex metadata are included in PR #68.
- [x] Atomic household enrollment is now routed through the proposed server-only RPC; the function has a fixed `pg_catalog` search path, per-Auth-user transaction lock, and restricted execution grants. Contract assertions cover these invariants. See the latest exact-head workflow on [PR #68](https://github.com/kaustubhdua/Saathi/pull/68); older runs do not certify newer commits.
- [x] Backend dependency audit passed; production-only npm audit reports zero vulnerabilities.
- [ ] PR #68 is still draft; do not merge until the live gates below are resolved.
- [ ] PR #58 is still draft because migration history across all relevant environments has not been reconciled.
- [ ] Vercel configuration/deployment is frozen until 24 October 2026.

## Before merge

- [ ] Latest exact-head CI is green after all current code and documentation updates: frontend lint, Node contract tests, TypeScript, production build, backend pytest/API smoke, dependency audit, Docker build and Streamlit smoke. The PR's latest check is authoritative.
- [ ] No secrets, real phone numbers, household data, access tokens or private provider payloads are present in source, logs, fixtures or artifacts.
- [ ] Frontend lockfile is committed and reproducible with `npm ci`.
- [ ] Five high-severity development-tool-chain npm audit findings (`eslint-config-next` / `fast-glob` / `micromatch` / `braces`) are recorded and risk-reviewed; do not use the suggested major downgrade. Production-only npm audit currently reports zero findings. Recheck upstream advisory status before release.
- [ ] The README, feature ledger, deployment runbook and acceptance matrix match the actual code and clearly label disabled integrations.

## Database and identity — BLOCKING

- [ ] Reconcile migration history for every Saathi target environment. The active Nihdhoom project has six recorded Saathi migrations; the separate inactive Saathi project was not restored because its history query timed out. Do not restore it without operator approval.
- [ ] Review PR #58's legacy migration quarantine and Saathi-only indexes; do not apply DDL while history remains ambiguous. Read-only inspection on 2026-10-16 confirmed `saathi_household_memberships` and `saathi_enroll_household` are absent from the active shared project.
- [ ] Review and activate the proposed `saathi_household_memberships` migration only after history reconciliation and an isolated-database dry run.
- [ ] Configure Supabase Phone Auth and SMS delivery; verify OTP send/verify, session refresh, sign-out, household PIN setup/verification, expiry and invalid-session handling.
- [ ] Verify phone-number recycling and concurrent first-login isolation with two distinct Auth identities. A phone number alone must never grant access to another household.
- [ ] Verify two-household isolation for tasks, memory, consent and volunteer cases using real non-production identities.
- [ ] Verify memory consent defaults off; user-entered memory save/list/delete works only with current consent; revocation purges stored memory; concurrent revoke/write cannot reintroduce memory. Automatic extraction remains disabled.
- [ ] Verify persisted purpose-specific outbound-call consent, including revocation, before any outbound-call feature can be enabled.

## Production configuration — BLOCKING

- [ ] Configure server-only `SUPABASE_SECRET_KEY`, `HOUSEHOLD_PIN_PEPPER`, `HOUSEHOLD_CONTEXT_SIGNING_SECRET`, `SAATHI_API_AUTH_TOKEN` and matching backend `API_AUTH_TOKEN`; never expose them through `NEXT_PUBLIC_*`.
- [ ] Configure Upstash Redis REST URL/token and the documented hosting-overwritten single-IP header. Test live shared rate limiting and fail-closed behavior when Redis/header configuration is missing.
- [ ] Keep `DEMO_MODE=true` until the real provider and identity acceptance tests pass.
- [ ] Verify API readiness, same-origin proxy, CORS, no-store/security headers, secret redaction and production-only configuration.

## Provider and workflow acceptance — BLOCKING

- [ ] Verify live Open-Meteo weather and OGD/AGMARKNET market data, including location matching, units, freshness timestamps and unavailable/stale responses.
- [ ] Verify real STT → tool → TTS from supported browsers/devices and record latency; do not infer success from mocked tests.
- [ ] Verify the actual Exotel callback contract. The current HMAC header requirement is not proven compatible with the deployed provider callback. Keep `TELEPHONY_CALLBACK_SIGNATURE_VERIFIED=false` and outbound calls disabled until verified.
- [ ] Implement and test durable reminder dispatch and volunteer case assignment/delivery; these are not enabled today.
- [ ] Verify callback idempotency, terminal-state monotonicity, retries, duplicate events and unauthorized callback rejection.

## Browser, accessibility and operations

- [ ] Test mobile and desktop layout on real browsers, including keyboard-only navigation, screen readers, visible focus, contrast, reduced motion, form validation and error/recovery states.
- [ ] Run a full WCAG 2.2 AA audit and Lighthouse/Core Web Vitals; record results rather than claiming accessibility/performance by appearance.
- [ ] Verify SEO metadata and keep the household demo noindex.
- [ ] Configure monitoring, structured logs, alerts, retention/privacy rules and provider failure visibility.
- [ ] Exercise backup/restore and rollback; confirm the deployed SHA matches the reviewed candidate.

## Deployment freeze and go-live

- [ ] Do not configure or deploy Vercel before 24 October 2026.
- [ ] After the freeze, deploy only when the blocking gates above are checked and PR merge/deployment behavior is understood.
- [ ] Smoke-test the exact deployed SHA: homepage, dashboard, anonymous chat, voice, auth/OTP, PIN, consent, task CRUD, explicit memory CRUD, provider failure paths and security headers.
- [ ] Save redacted evidence, rollback instructions and the final deployed SHA in the release record.

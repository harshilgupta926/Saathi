# Saathi Release Feature Ledger

Last verified: 2026-10-15 UTC (2026-10-16 IST)

- Main baseline after PR #64: `fb795e62f5dbaaf6d57ef150e2877382c8a32655`.
- P0/P1 proxy and freshness: [PR #57](https://github.com/kaustubhdua/Saathi/pull/57), merged.
- Household identity fail-closed guard: [PR #59](https://github.com/kaustubhdua/Saathi/pull/59), merged.
- Telephony callback lifecycle and live-call safety gate: [PR #61](https://github.com/kaustubhdua/Saathi/pull/61), merged.
- Migration quarantine/index proposal: [PR #58](https://github.com/kaustubhdua/Saathi/pull/58), draft; do not merge until all environments' migration histories are reconciled.
- Shared production API rate limiting: [PR #64](https://github.com/kaustubhdua/Saathi/pull/64), merged as `fb795e62f5dbaaf6d57ef150e2877382c8a32655`.
- [Release acceptance matrix](RELEASE_ACCEPTANCE_MATRIX.md)
- [Provider verification plan](PROVIDER_VERIFICATION.md)
- Deployment policy: no Vercel production deployment before 2026-10-24.

## Verified

- The Nihdhoom project was reviewed read-only and contained eight Saathi-prefixed tables with RLS enabled and browser-role access denied.
- PR #57 merged as `e8a13bdd0022f33707e6a9338d3cc7fcdf039615`; exact-head CI run #770 passed all five jobs, and main run #771 passed.
- PR #59 merged as `d048170180a24a36280c557150753c687139d9d7`; exact-head CI run #774 passed all five jobs. Production text/voice routes reject caller-supplied household UUIDs until verified identity-to-household ownership exists.
- PR #64 merged as `fb795e62f5dbaaf6d57ef150e2877382c8a32655`; GitHub Actions run #796 passed all five jobs on PR head `b6820fae1e7fbf70cebc931eb3647abdf864a293` (frontend lint/tests/TypeScript/build/dashboard smoke, backend pytest/API smoke, dependency audit, Docker build, Streamlit smoke).
- Production proxy requests now require a configured shared Upstash limiter and trusted single-IP header; absent or invalid configuration fails closed. Live Upstash and hosting-header behavior remain unverified.
- No live database migration or production deployment was performed.

## Partial

- **Dashboard accessibility (PR #63):** scenario tabs use roving tabindex with arrow/Home/End keyboard navigation; API/voice/answer state announcements use live regions; microphone controls expose pressed state; the UI no longer claims consent was collected. This is a code-level contract check, not a full WCAG 2.2 AA audit.
- Frontend API calls use a same-origin allowlisted proxy; the server injects the API token and production readiness fails closed without operator auth.
- Scheme catalogue data carries reviewed/stale/unknown freshness rather than a false live retrieval timestamp. Mandi records with invalid, future or over-seven-day observations are withheld from current-price claims.
- Consent and task repositories and Saathi schema protections exist, but verified user identity, consent UI/API, household memory/tasks/case workflows and cross-household integration tests remain incomplete.
- PR #61 merged signed form/JSON callback parsing, body-derived idempotency, monotonic call status transitions, server-configured public HTTPS callback URL, and a hard gate preventing live calls until the actual callback authentication contract is verified.
- PR #64 bounds the development limiter to 2,000 buckets and adds the atomic production shared limiter. Production still requires operator provisioning of Upstash and verification of the trusted IP header.

## Blocked / not tested

- PR #58 remains draft: reconcile migration histories in every relevant environment before merge or live DDL.
- No real Open-Meteo, OGD/AGMARKNET, Sarvam STT/TTS, document AI or Exotel round-trip test is claimed.
- Exotel callback authentication remains unverified: the current webhook requires an HMAC over the raw body, and official callback docs do not establish that Exotel supplies the custom HMAC header. Keep `TELEPHONY_CALLBACK_SIGNATURE_VERIFIED=false` until verified with the actual provider or trusted signer.
- The frontend lockfile is committed in PR #66; GitHub Actions run #809 passed all five jobs on candidate SHA `b08cb8c410413c41c963ceab3464420013cb7f5b`, including `npm ci`, lint, tests, TypeScript, build, dashboard smoke and dependency audit. Mobile/browser accessibility checks, Lighthouse/Core Web Vitals, SEO, monitoring, rollback evidence and deployed SHA remain outstanding.
- Vercel deployment/configuration remains deferred until 2026-10-24.

## Next actions

1. Keep live telephony disabled until the provider's callback signature contract is proven in a sandbox.
2. Keep PR #58 draft until migration history is reconciled across environments.
3. Implement verified user sessions and identity-to-household ownership before enabling household memory/task APIs.
4. Test real providers with authorized credentials and attach redacted evidence.
5. Complete durable reminder/volunteer workflows, accessibility/performance checks, reproducible builds and rollback evidence.
6. Deploy only after 2026-10-24 and only after the release matrix gates are satisfied.


## Merged change — PR #64

- [PR #64](https://github.com/kaustubhdua/Saathi/pull/64) adds a bounded 2,000-entry local development limiter and a production-only atomic Upstash Redis fixed-window limiter.
- Production requests fail closed when the shared store is absent/unavailable, the trusted single-IP header is missing/invalid, or Redis returns an invalid counter. The Redis key contains an HMAC digest rather than a raw IP address.
- Added regression tests for high-cardinality input, malformed IP values, invalid Upstash host/port, missing configuration, outage, response type validation, over-limit handling, and pseudonymous key construction.
- Status: **merged; exact-head CI passed**. Run #796 passed all five jobs on PR head `b6820fae1e7fbf70cebc931eb3647abdf864a293`. The local environment could not clone GitHub, so no local full build is claimed.
- Operational dependency: provision the shared Upstash REST store and verify the hosting proxy overwrites the configured IP header before production traffic is enabled. This change intentionally fails closed until configured.


## Engineering sprint — dashboard failure-path hardening (2026-10-16)

- Branch: `fix/dashboard-fail-closed-agent-errors`.
- Change: agent requests now have a 20-second abort timeout, validate the minimum response contract, clear stale answers before a new request, and render failures in a separate accessible alert with retry. The catch path no longer creates a synthetic `Result`.
- Regression coverage: `frontend/tests/agent-error-contract.test.mjs` checks timeout/abort wiring, malformed response rejection, stale-result clearing, accessible error state, retry control, and absence of the previous fabricated-result pattern.
- Verification: exact-head CI run [#953](https://github.com/kaustubhdua/Saathi/actions/runs/38804190786) passed on dashboard candidate SHA `5f58b25d84296c059aab5fcb54f5b516a2036b5e`. Later telephony changes passed exact-head CI run [#957](https://github.com/kaustubhdua/Saathi/actions/runs/38812480101) on SHA `4f1133b3dcd94914a33ec2b73b40add64991143e`. Later ledger/matrix commits trigger a fresh exact-head run; verify the current PR head before merge. CI does not establish production behavior.
- Production: not deployed; deployed SHA and real backend journey remain unverified. No database or provider configuration changed.

- CI verification update (2026-10-16): GitHub Actions run [#953](https://github.com/kaustubhdua/Saathi/actions/runs/38804190786) completed successfully on PR head `5f58b25d84296c059aab5fcb54f5b516a2036b5e`. All five jobs passed: backend pytest/API smoke, frontend `npm ci`/lint/regression tests/TypeScript/build/dashboard smoke, Streamlit smoke, dependency audit, and Docker build. This verifies the candidate code at that SHA, not production behavior. Any subsequent commit requires a fresh exact-head CI result.


## Engineering sprint — demo telephony truthfulness (2026-10-16 IST / 2026-10-15 UTC)

- Changed `POST /api/v1/calls` in non-production demo mode to return HTTP 503 with `telephony_unavailable_in_demo_mode`. It no longer returns the synthetic `demo-call-accepted` ID or a success-looking status.
- The demo path emits only a capability-unavailable event; a regression test patches the Exotel adapter to fail if invoked and verifies the response contains no call ID or acceptance claim.
- Code and test committed to branch `fix/dashboard-fail-closed-agent-errors`.
- Exact-head GitHub Actions run [#957](https://github.com/kaustubhdua/Saathi/actions/runs/38812480101) passed all five jobs on code SHA `4f1133b3dcd94914a33ec2b73b40add64991143e`. After the ledger/matrix cleanup, exact-head run [#959](https://github.com/kaustubhdua/Saathi/actions/runs/38812734100) also passed all five jobs on SHA `cff8b3ca9f41efcb6a0a7ad13ff2324763c300a2`. The current documentation refresh requires a fresh exact-head CI run before merge. CI does not establish production behaviour.
- Demo phone calling is **UNAVAILABLE**. Production telephony remains **NOT VERIFIED** pending real Exotel sandbox acceptance, persisted purpose-specific consent, and a verified callback-authentication contract. No live call, database mutation, provider activation, or deployment was performed.


## Engineering sprint — voice upload validation (2026-10-16 IST)

- The voice endpoint now normalizes MIME types with codec parameters (for example, `audio/webm;codecs=opus`) before allowlist comparison, while still requiring an explicit supported audio type.
- After the existing bounded 8 MB read, WAV uploads must have a RIFF/WAVE container signature and WebM uploads must have the EBML header. A spoofed MIME/header mismatch returns HTTP 415 before bytes reach STT/TTS providers.
- Regression coverage checks malformed WebM, malformed WAV, cross-container MIME spoofing, and confirms codec-qualified WebM MIME reaches the provider boundary after signature validation; the provider is patched to fail if invalid media reaches it.
- Initial exact-head CI run #963 found an expected-contract regression in `tests/test_health.py`: the provider-gating test did not allow HTTP 415 for malformed audio. The test was corrected. Exact-head CI run [#976](https://github.com/kaustubhdua/Saathi/actions/runs/38819660836) then passed all five jobs on SHA `afc7889000571492d19efeaf5ee6361c2c6ff484`; PR #79 was merged as `a30e1a9152c10e8219d8f6857d64f65eda5cd654`. No provider call, database write, or deployment was performed.
- Remaining: add bounded request-level timeout/cancellation and confirm browser-produced media fixtures against real low-end Android capture before enabling any live provider path.


## Engineering sprint — scheme effective-date provenance (2026-10-16 IST)

- Scheme records now expose `effective_from` separately from `source_checked_on`, plus an explanatory `effective_date_note`; the API serializes these fields through its existing dataclass response.
- PM-KISAN operational date: `2018-12-01`, as stated on the [official PM-KISAN portal](https://pmkisan.gov.in/).
- PMFBY inception is represented as `Kharif 2016`, matching the [official PMFBY guidelines](https://pmfby.gov.in/pdf/Revamped%20Operational%20Guidelines_17th%20August%202020.pdf). The record explicitly warns that current state/crop/season notifications may have separate effective dates and deadlines.
- The catalogue review date is `2026-10-15` UTC / `2026-10-16` IST; this records the review, not a live government data feed. Regression tests assert both effective-date fields and the distinction from current eligibility/season rules.
- Verification: exact-head CI run [#976](https://github.com/kaustubhdua/Saathi/actions/runs/38819660836) passed all five jobs on candidate SHA `afc7889000571492d19efeaf5ee6361c2c6ff484`; PR #79 merged as `a30e1a9152c10e8219d8f6857d64f65eda5cd654`. No scheme eligibility is inferred from these inception dates, and no application is submitted automatically.


## Merged engineering sprint — PR #79 (2026-10-16 IST)

- Merge commit: `a30e1a9152c10e8219d8f6857d64f65eda5cd654`; source branch head: `afc7889000571492d19efeaf5ee6361c2c6ff484`.
- Exact-head CI [run #976](https://github.com/kaustubhdua/Saathi/actions/runs/38819660836) passed all five jobs: backend pytest/API smoke, frontend lockfile install/lint/tests/TypeScript/build/dashboard smoke, Streamlit smoke, dependency audit and Docker build.
- Merged changes: dashboard bounded timeout/fail-closed errors; demo telephony explicit 503 unavailable instead of synthetic acceptance; voice MIME normalization and WAV/WebM signature validation before provider invocation; explicit scheme effective-from metadata and source-review dates.
- Follow-up main CI was triggered on the merge commit. The ledger-only follow-up commit will also trigger a fresh main CI run; production behavior remains unverified and no deployment occurred.

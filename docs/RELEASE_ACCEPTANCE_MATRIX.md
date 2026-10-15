# Saathi release acceptance matrix

Last updated: 2026-10-15 UTC (2026-10-16 IST)

This is an evidence ledger, not a declaration that release gates have passed. Automated CI and manual/live-provider acceptance are tracked separately. A checked item must link to reproducible evidence for the exact candidate SHA.

## Current baseline

- Main after P0/P1 merge: `e8a13bdd0022f33707e6a9338d3cc7fcdf039615`.
- PR #59 adds production fail-closed behavior for unverified household identifiers; CI run #772 is pending at the time this document was authored.
- PR #58 remains draft because other environments' migration histories are not verified.
- Production Vercel configuration/deployment remains deferred until 2026-10-24.
- No live provider test, live database DDL, or production deployment is claimed here.

## Manual release gates

| # | Acceptance gate | Status | Evidence required |
|---|---|---|---|
| 1 | Browser API requests use the same-origin allowlisted proxy; server token never enters browser bundles | PARTIAL | PR #57 merged and exact-head CI green; inspect production build/environment and run hosted request tests |
| 2 | Production readiness fails when operator auth is absent | CODE + CI | Backend test and exact-main CI; verify real deployment configuration |
| 3 | Identity-to-household ownership is verified; caller-supplied UUID cannot select another household | PARTIAL / FAIL-CLOSED | PR #59 denies unverified IDs; verified identity provider and ownership journey not implemented |
| 4 | Consent grant/status/revocation are persisted and identity-bound | NOT COMPLETE | Implement user identity and consent endpoints; test revocation and denial |
| 5 | Memory writes require current consent; revocation deletes memory | SCHEMA FOUNDATION ONLY | Test real repository path and concurrent revoke/write behavior against isolated test DB |
| 6 | Two households cannot read/update each other's tasks, memory or cases | NOT COMPLETE | Two-identity integration tests against non-production database |
| 7 | Live weather and mandi results have correct source and observation/retrieval timestamps | NOT VERIFIED | Authorized provider tests; validate units, location matching, freshness and failure cases |
| 8 | Browser voice completes real STT -> tool -> TTS with measured latency | NOT VERIFIED | Provider credentials, browser matrix, STT/TTS round-trip logs and p50/p95 latency |
| 9 | Outbound phone calls require persisted purpose-specific consent; webhooks update call lifecycle idempotently | PARTIAL / PROVIDER BLOCKED | Demo mode now returns explicit 503 `telephony_unavailable_in_demo_mode` and never emits a synthetic accepted call ID. Production still requires persisted purpose-specific consent, real Exotel sandbox proof, and verified callback authentication. |
| 10 | Reminder/volunteer workflows persist, dispatch, retry, assign and resolve correctly | NOT COMPLETE | Durable dispatcher, atomic claims, retry/quiet-hour tests and operator queue evidence |
| 11 | Mobile, keyboard, screen-reader, reduced-motion and WCAG 2.2 AA-oriented checks pass | NOT VERIFIED | Device/browser test results and accessibility audit |
| 12 | Production performance, SEO, monitoring, rollback and deployed SHA are recorded | NOT VERIFIED | Lighthouse/Core Web Vitals, metadata checks, alerts/runbook, hosted smoke and rollback rehearsal |

## Automated verification

- CI on PR #57 head `03483bc3450a08cad161765494758e06c3093cec`: all five jobs passed; PR was subsequently merged.
- Main push run #771 on `e8a13bdd0022f33707e6a9338d3cc7fcdf039615`: success.
- PR #59 exact-head run #772: check its live status before merge.
- CI uses `npm ci` with the committed `frontend/package-lock.json` (PR #66); the frontend and dependency-audit jobs verify lockfile-based installation. This does not establish hosted or provider-backed behaviour.
- CI provider tests are stubs/smoke checks and do not prove live weather, mandi, Sarvam, document AI or Exotel functionality.

## Data-safety rules

- Only `saathi_*` tables may be changed in the shared Nihdhoom project.
- Do not run a migration push or apply the index migration until all relevant environments' migration histories are reconciled.
- Do not change unrelated Telegram tables, shared SECURITY DEFINER functions, or unused shared indexes as part of Saathi.
- Keep secrets server-side; never use `NEXT_PUBLIC_*` for API/provider tokens.
- Do not deploy Vercel before 2026-10-24.


## Merged change — PR #64

| Gate | Candidate status | Required next evidence |
|---|---|---|
| Shared production rate limit | Merged as `fb795e62f5dbaaf6d57ef150e2877382c8a32655`; run #796 passed all five jobs on PR head `b6820fae1e7fbf70cebc931eb3647abdf864a293` | All exact-head CI jobs green; verify Upstash and trusted-IP header in the deployment environment before enabling production |
| Local limiter memory bound | Merged; frontend test suite passed in run #796 | Exact-head frontend test suite green |
| Live shared-store behavior | Not verified | Authorized non-production Redis test with redacted evidence; no credentials in Git or chat |


## Frontend dependency reproducibility — PR #66

- A committed `frontend/package-lock.json` was generated by the repository's own Node 24 CI install (not handwritten or inferred).
- The frontend and dependency-audit jobs now use `npm ci` and the setup-node cache keys off the lockfile.
- GitHub Actions run #809 passed all five jobs on candidate SHA `b08cb8c410413c41c963ceab3464420013cb7f5b`, including lockfile integrity, `npm ci`, lint, tests, TypeScript, build, dashboard smoke and dependency audit. Live provider/production verification remains separate.


## Sprint 27 verification note — 2026-10-16 IST / 2026-10-15 UTC

The demo telephony fail-closed change is committed on `fix/dashboard-fail-closed-agent-errors`. Exact-head run [#957](https://github.com/kaustubhdua/Saathi/actions/runs/38812480101) passed on code SHA `4f1133b3dcd94914a33ec2b73b40add64991143e`; follow-up exact-head run [#959](https://github.com/kaustubhdua/Saathi/actions/runs/38812734100) passed all five jobs on SHA `cff8b3ca9f41efcb6a0a7ad13ff2324763c300a2`. This establishes automated CI only, not real provider acceptance. The current documentation refresh requires another exact-head CI run. Do not mark the telephony gate complete until live provider acceptance and callback authentication have separate sandbox evidence.


## Sprint note — voice upload boundary (2026-10-16 IST)

- Code-level acceptance: supported MIME types are normalized for codec parameters; WAV/WebM magic bytes are checked after a bounded read; mismatches return 415 before provider invocation; regression tests cover spoofing and codec-qualified WebM acceptance.
- Status: CODE + CI PENDING. Run #963 caught an existing voice endpoint contract test that did not include HTTP 415; this was updated to reflect the intended fail-closed malformed-media response. The follow-up exact-head run must pass. This is not a live browser/provider test and does not establish full media-parser safety. Validate actual browser-produced WebM/WAV fixtures on supported mobile browsers before release.


## Sprint note — scheme dates (2026-10-16 IST)

- Scheme API payload now carries a distinct scheme inception/effective-from field, source review date (2026-10-15 UTC / 2026-10-16 IST) and explanatory caveat. PM-KISAN uses 2018-12-01; PMFBY uses the non-date-specific season label Kharif 2016, per official source wording.
- Status: CODE + CI PENDING. This does not establish current state-wise eligibility, crop-season deadline or a live scheme catalogue feed. Those must be confirmed against the current official notice before advising an application.

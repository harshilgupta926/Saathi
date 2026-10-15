# Saathi release acceptance matrix

Last updated: 2026-10-15 UTC

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
| 9 | Outbound phone calls require persisted purpose-specific consent; webhooks update call lifecycle idempotently | PARTIAL | Consent lookup exists; event processing into durable call-state transitions and provider signature contract remain |
| 10 | Reminder/volunteer workflows persist, dispatch, retry, assign and resolve correctly | NOT COMPLETE | Durable dispatcher, atomic claims, retry/quiet-hour tests and operator queue evidence |
| 11 | Mobile, keyboard, screen-reader, reduced-motion and WCAG 2.2 AA-oriented checks pass | NOT VERIFIED | Device/browser test results and accessibility audit |
| 12 | Production performance, SEO, monitoring, rollback and deployed SHA are recorded | NOT VERIFIED | Lighthouse/Core Web Vitals, metadata checks, alerts/runbook, hosted smoke and rollback rehearsal |

## Automated verification

- CI on PR #57 head `03483bc3450a08cad161765494758e06c3093cec`: all five jobs passed; PR was subsequently merged.
- Main push run #771 on `e8a13bdd0022f33707e6a9338d3cc7fcdf039615`: success.
- PR #59 exact-head run #772: check its live status before merge.
- CI uses `npm install`, not `npm ci`; frontend lockfile reproducibility remains open.
- CI provider tests are stubs/smoke checks and do not prove live weather, mandi, Sarvam, document AI or Exotel functionality.

## Data-safety rules

- Only `saathi_*` tables may be changed in the shared Nihdhoom project.
- Do not run a migration push or apply the index migration until all relevant environments' migration histories are reconciled.
- Do not change unrelated Telegram tables, shared SECURITY DEFINER functions, or unused shared indexes as part of Saathi.
- Keep secrets server-side; never use `NEXT_PUBLIC_*` for API/provider tokens.
- Do not deploy Vercel before 2026-10-24.

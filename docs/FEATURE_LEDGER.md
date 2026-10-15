# Saathi Release Feature Ledger

Last verified: 2026-10-15 UTC

- Main baseline: `d048170180a24a36280c557150753c687139d9d7` after PR #59.
- P0/P1 proxy and freshness: [PR #57](https://github.com/kaustubhdua/Saathi/pull/57), merged.
- Household identity fail-closed guard: [PR #59](https://github.com/kaustubhdua/Saathi/pull/59), merged.
- Telephony callback lifecycle and live-call safety gate: [PR #61](https://github.com/kaustubhdua/Saathi/pull/61), merged.
- Migration quarantine/index proposal: [PR #58](https://github.com/kaustubhdua/Saathi/pull/58), draft; do not merge until all environments' migration histories are reconciled.
- [Release acceptance matrix](RELEASE_ACCEPTANCE_MATRIX.md)
- [Provider verification plan](PROVIDER_VERIFICATION.md)
- Deployment policy: no Vercel production deployment before 2026-10-24.

## Verified

- The Nihdhoom project was reviewed read-only and contained eight Saathi-prefixed tables with RLS enabled and browser-role access denied.
- PR #57 merged as `e8a13bdd0022f33707e6a9338d3cc7fcdf039615`; exact-head CI run #770 passed all five jobs, and main run #771 passed.
- PR #59 merged as `d048170180a24a36280c557150753c687139d9d7`; exact-head CI run #774 passed all five jobs. Production text/voice routes reject caller-supplied household UUIDs until verified identity-to-household ownership exists.
- No live database migration or production deployment was performed.

## Partial

- **Dashboard accessibility (PR #63):** scenario tabs use roving tabindex with arrow/Home/End keyboard navigation; API/voice/answer state announcements use live regions; microphone controls expose pressed state; the UI no longer claims consent was collected. This is a code-level contract check, not a full WCAG 2.2 AA audit.
- Frontend API calls use a same-origin allowlisted proxy; the server injects the API token and production readiness fails closed without operator auth.
- Scheme catalogue data carries reviewed/stale/unknown freshness rather than a false live retrieval timestamp. Mandi records with invalid, future or over-seven-day observations are withheld from current-price claims.
- Consent and task repositories and Saathi schema protections exist, but verified user identity, consent UI/API, household memory/tasks/case workflows and cross-household integration tests remain incomplete.
- PR #61 proposes signed form/JSON callback parsing, body-derived idempotency, monotonic call status transitions, server-configured public HTTPS callback URL, and a hard gate preventing live calls until the actual callback authentication contract is verified.

## Blocked / not tested

- PR #58 remains draft: reconcile migration histories in every relevant environment before merge or live DDL.
- No real Open-Meteo, OGD/AGMARKNET, Sarvam STT/TTS, document AI or Exotel round-trip test is claimed.
- Exotel callback authentication remains unverified: the current webhook requires an HMAC over the raw body, and official callback docs do not establish that Exotel supplies the custom HMAC header. Keep `TELEPHONY_CALLBACK_SIGNATURE_VERIFIED=false` until verified with the actual provider or trusted signer.
- A reviewed frontend lockfile and `npm ci`, mobile/browser accessibility checks, Lighthouse/Core Web Vitals, SEO, monitoring, rollback evidence and deployed SHA remain outstanding.
- Vercel deployment/configuration remains deferred until 2026-10-24.

## Next actions

1. Wait for CI on PR #61 and fix all failures before merge.
2. Keep PR #58 draft until migration history is reconciled across environments.
3. Implement verified user sessions and identity-to-household ownership before enabling household memory/task APIs.
4. Test real providers with authorized credentials and attach redacted evidence.
5. Complete durable reminder/volunteer workflows, accessibility/performance checks, reproducible builds and rollback evidence.
6. Deploy only after 2026-10-24 and only after the release matrix gates are satisfied.

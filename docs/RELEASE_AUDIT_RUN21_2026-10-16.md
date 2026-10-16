# Saathi Release Audit — Run 21

Date: 2026-10-16 UTC  
Scope: GitHub branch review, static security hardening, read-only Supabase verification, and release evidence refresh. No live DDL, migration push, provider activation, project restoration, or deployment was performed.

## Current GitHub work

- Integrated candidate: [PR #68](https://github.com/kaustubhdua/Saathi/pull/68), open and draft.
- Migration-safety candidate: [PR #58](https://github.com/kaustubhdua/Saathi/pull/58), open and draft.
- Accessibility/error-state PR #76 is closed without merge because its changes are consolidated into PR #68.
- Exact-tree validation PR #77 run #945 passed all five CI jobs on `0d8a68aaa471370d4aed065b7b1b238726c50c12`; PR #77 was closed after validation. PR #68 remains the integration candidate. Any subsequent commit requires a fresh exact-head run.

### Atomic household enrollment hardening

Published on the PR #68 branch:
- The frontend server calls the proposed `saathi_enroll_household` RPC rather than performing household creation and membership creation as separate REST requests.
- The RPC uses a transaction-scoped advisory lock keyed to the immutable Auth user ID.
- It does not adopt a household based on a phone-number collision; if the phone is already assigned, it creates a new household without attaching that phone.
- Direct writes to `saathi_household_memberships` are revoked from `service_role`; SELECT remains available for identity lookup. RPC execution is granted only to `service_role`.
- The `SECURITY DEFINER` function now uses `SET search_path = pg_catalog`; referenced application tables and advisory-lock functions are schema-qualified.
- Frontend contract tests assert the RPC boundary, serialization lock, restricted search path, and role grants.

The SQL remains under `docs/proposed-migrations/`. This is published code plus static contract coverage, not proof that the SQL has been executed against PostgreSQL. Before activation, review the function owner, actual grants after migration, return shape, conflict behavior, and deterministic concurrent-enrollment behavior in an authorized isolated database.

## Read-only Supabase verification

Active shared project: `igqgtlmnwssjaoxkkzbm` (Nihdhoom, `ap-south-1`).

- Migration inventory contains six Saathi migration records, through `saathi_atomic_webhook_event_persistence`.
- `public.saathi_households` exists with unique nullable `phone_number` and consent defaults set to false.
- `public.saathi_household_memberships` does not exist.
- `public.saathi_enroll_household(uuid, text, text)` does not exist.
- Therefore the current household OTP/PIN path cannot be considered live-ready; it must fail closed until the migration is approved, applied to the correct target, and verified.
- The separate Supabase project named `Saathi` (`ibvgxgvcqcfnoyrlwywa`, `ap-northeast-2`) remains inactive. Its migration-history query previously timed out. It was not restored. Do not restore it without explicit operator approval.
- The active project is shared with Nihdhoom and other namespaced components. Its broad advisor report includes findings on unrelated functions/tables. Do not apply broad fixes to unrelated applications as part of Saathi without a scoped review.

## Hosting discovery

Read-only Vercel discovery found no Vercel project linked to `kaustubhdua/Saathi`; the connected team currently lists JYC Website, SATARK, and Nihdhoom projects. No Saathi deployment was created or changed. The documented freeze against Vercel configuration/deployment remains in force until 2026-10-24, and the post-freeze setup must select the intended Supabase target and satisfy the release gates first.

## CI and quality gates

The workflow includes frontend lint, Node contract tests, TypeScript, production build and dashboard smoke; backend tests and API smoke; dependency audit; Docker build; and Streamlit smoke. Run #945 passed all five jobs on the exact candidate tree, including the new bounded streaming JSON parser tests for OTP/verify/PIN. See [PR #68](https://github.com/kaustubhdua/Saathi/pull/68).

The full frontend dependency tree has previously reported five high-severity development-tool-chain advisories. Production-only `npm audit --omit=dev --audit-level=high` passes. Do not force a major Next/ESLint downgrade; record and reassess upstream advisories before release.

## Blocking release gates

1. Reconcile migration history for every intended target environment. PR #58 must remain draft until the inactive target is safely understood.
2. Apply the membership schema and RPC only after the target is explicitly selected, history is reconciled, and a reviewed isolated dry run passes.
3. Verify SQL owner, effective privileges, RLS, RPC permissions, row-return shape, same-user concurrency, cross-household isolation, phone recycling, PIN immutability, and consent-revocation races.
4. Configure Supabase Phone Auth/SMS and server-only secrets, then test OTP, session refresh, PIN setup/verification, sign-out, rate limiting, and invalid-session behavior.
5. Verify live weather/mandi sources and timestamps, browser STT→tool→TTS, and the real Exotel callback authentication contract. Keep live calls disabled until provider acceptance is documented.
6. Complete browser E2E, mobile/desktop keyboard and screen-reader testing, WCAG 2.2 AA review, Lighthouse/Core Web Vitals, hosted smoke tests, monitoring and rollback evidence.
7. Resolve or formally risk-accept development dependency advisories.
8. Do not configure or deploy Vercel before 2026-10-24. After the freeze, deployment still requires P0 acceptance gates, exact-head CI, production smoke tests, and a rollback plan.

## Release decision

**Not production-approved.** The repository has a CI-validated implementation candidate and updated release evidence, but live identity, membership migration, cross-household isolation, provider acceptance, and deployment gates remain unverified. Do not merge or claim full production completion until those gates have evidence.
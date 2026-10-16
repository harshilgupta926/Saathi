# Saathi Release Audit — Run 22

Date: 2026-10-16 UTC  
Scope: exact-head GitHub CI revalidation, candidate source review, and release evidence reconciliation. No live database writes/DDL, migration push, provider activation, inactive-project restoration, or Vercel deployment/configuration was performed.

## Exact repository checkpoint

- Main: `edd5164fc406b87a5ab811d9746ad21e7e4c1d1f`.
- Integrated candidate: [PR #68](https://github.com/kaustubhdua/Saathi/pull/68), open and draft.
- Candidate head at the start of this audit: `23d954f5c323f0847a7c7a44d11e47894e334f95`.
- GitHub Actions run [#948](https://github.com/kaustubhdua/Saathi/actions/runs/38788384830) passed all five jobs on that exact SHA:
  - **frontend:** `npm ci`, lint, Node tests, TypeScript, Next production build, built-dashboard smoke.
  - **backend:** pytest and running API smoke.
  - **dependency-audit:** backend pip-audit and production npm audit.
  - **docker-build:** production API image build and image metadata/entrypoint check.
  - **streamlit-smoke:** Python compile check.
- The full-tree frontend audit still reports known high-severity development-tool-chain advisories; production-only audit passes. CI green is not equivalent to production acceptance.

## Security/source review

- `frontend/lib/auth-rate-limit.mjs` validates the configured trusted client-IP header and rejects missing, malformed, or comma-separated values in production before Upstash calls. Production also fails closed if shared Upstash configuration is missing or malformed.
- OTP, OTP verification, and household PIN mutations require JSON and use `readBoundedJson`, which bounds both bytes and read duration. Contract tests assert the routes use this parser rather than unbounded `request.text()`.
- Household routes resolve identity server-side from a confirmed Supabase phone identity, an HMAC-signed HTTP-only context cookie, and the membership row. Caller-supplied household IDs are not used as the authorization source.
- Task idempotency-conflict recovery is household-filtered; repository responses are checked against the verified household. Memory writes are explicit user submissions and require current memory consent. Automatic conversation extraction and automatic reminder/callback dispatch remain disabled.
- The membership enrollment migration is still a proposal outside `supabase/migrations`; the live shared project does not yet contain `saathi_household_memberships` or `saathi_enroll_household`. Household-specific routes must remain fail-closed until that schema is reviewed and safely activated.

## Database migration reconciliation

- Active shared Nihdhoom project `igqgtlmnwssjaoxkkzbm` has six recorded Saathi migrations in its live migration history, while the repository branch contains two older unprefixed legacy migration files plus six timestamped Saathi migrations. The live active project does not show the two legacy versions. Do not infer that other environments match.
- The separate Supabase project named `Saathi` (`ibvgxgvcqcfnoyrlwywa`) is inactive; its migration-history query timed out. It was not restored. That environment remains unverified.
- PR #58 remains draft. Do not merge it, activate proposed membership SQL, or push migrations until the owner identifies every target environment, the inactive environment is safely reviewed with explicit approval, and histories are reconciled without destructive repair.

## Remaining acceptance gates

1. Isolated-database tests: enrollment RPC grants/owner/return shape; same-user concurrent enrollment; recycled phone; PIN immutability; two-household task/memory isolation; consent revocation racing a memory write; RLS/effective privileges.
2. Provider tests: real Supabase Phone Auth/SMS and session refresh; live Upstash shared counter and hosting overwrite of the trusted single-IP header; authorized weather/AGMARKNET freshness; browser STT→tool→TTS; exact Exotel callback authentication/payload contract.
3. Product workflows: durable reminder/callback dispatch, retries, idempotency, quiet hours, receipts, volunteer assignment/delivery, webhook replay processing, and deletion/retention acceptance.
4. Accessibility/performance: real device/browser keyboard and screen-reader checks, WCAG 2.2 AA audit, Lighthouse/Core Web Vitals, hosted browser smoke, monitoring and rollback rehearsal.
5. Release operations: deployment target/configuration and deployed SHA are unverified. No Vercel deployment or configuration is permitted before 2026-10-24; afterward the release gates and explicit operator approval still apply.

## Decision

**Not production-approved.** Code and exact-head CI are verified on the candidate SHA above, but live database schema, provider behavior, end-to-end identity and consent, full task/callback workflows, accessibility/performance, and production deployment are not all verified. Keep PR #68 and PR #58 open as drafts; do not merge or claim the website fully complete.
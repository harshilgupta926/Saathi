# Saathi Release Audit — Run 23

Date: 2026-10-16 UTC  
Scope: follow-up exact-head CI verification and review of household enrollment migration hardening. This audit makes no claim of production readiness. No live database writes/DDL, migration push, provider activation, inactive-project restoration, or Vercel deployment/configuration was performed.

## Repository and CI evidence

- Candidate: [PR #68](https://github.com/kaustubhdua/Saathi/pull/68), open and draft.
- Candidate head verified: `1c295c4cb92968d4c1f74e3024af91cf921d1805`.
- GitHub Actions [run #949](https://github.com/kaustubhdua/Saathi/actions/runs/38788807380) completed successfully on that exact head. All five jobs passed:
  - Frontend: `npm ci`, lint, Node contract tests, TypeScript, Next production build and built-dashboard smoke.
  - Backend: pytest and running API smoke.
  - Dependency audit: backend `pip-audit` and production-only npm audit. The full frontend development dependency tree still reports advisories; the strict production dependency audit passes.
  - Docker production API image build and metadata/entrypoint check.
  - Streamlit smoke/compile check.

## Additional security hardening committed during follow-up

- Restricted the proposed SECURITY DEFINER household-enrollment RPC's search path to `pg_catalog`, avoiding writable `public` objects in the privileged function's name-resolution path.
- Added regression assertions for the restricted search path, per-user advisory transaction lock, and explicit execute grants/revocations.
- These changes are in the release branch. CI for this follow-up change must run against its new exact head before it is considered verified.

## Hard blockers remain

1. The membership migration and `saathi_enroll_household` RPC are still not deployed to the active shared database. Do not activate them until migration history is reconciled across every target environment.
2. The separate Supabase project named Saathi is inactive and its migration history remains unverified. It was not restored; restoration requires explicit operator approval.
3. Real Supabase Phone Auth/SMS, session lifecycle, PIN setup/verification, recycled-number isolation, two-household data isolation, and concurrent memory-revocation/write behavior still require isolated live tests.
4. Upstash shared rate limiting and trusted client-IP header behavior require real hosting configuration and verification.
5. Weather/mandi source freshness, browser STT-to-tool-to-TTS, and the exact telephony callback authentication/payload contract need live provider acceptance. Outbound calls remain disabled unless consent and callback authentication are verified.
6. Durable reminder delivery, volunteer assignment/delivery, webhook replay handling, retention/deletion, accessibility and performance acceptance, hosted browser smoke, monitoring and rollback rehearsal remain incomplete.
7. Deployment target/configuration is not verified. The repository's freeze prohibits Vercel deployment/configuration before 2026-10-24; after that date, release gates and operator approval still apply.

## Release decision

**Not production-approved.** Run #949 proves the then-current candidate's CI, not production integration. Keep PR #68 and PR #58 as drafts, keep demo-safe behavior, and do not claim all functionality is complete until the database, providers, hosted environment and end-to-end acceptance evidence are in place.
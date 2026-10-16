# Saathi Release Sprint — Run 20

Date: 2026-10-15 (IST) — superseded by the Run 21 audit dated 2026-10-16  
Scope: evidence-only refresh; no merge, database mutation, provider activation, or deployment.

## Live GitHub state checked at run start

- Integrated PR #68 is open and draft, head `4b4cedb8b73cc645192cf0f616d109f792209543`, base `main` at `edd5164fc406b87a5ab811d9746ad21e7e4c1d1f`.
- Exact-head Actions run #921 for that SHA completed successfully: frontend lint/contract tests/TypeScript/build/dashboard smoke, backend tests/API smoke, dependency audit, Docker build, and Streamlit smoke all passed.
- Migration-safety PR #58 is open and draft, head `bb0b9c50dd3c0eb2d2d09dde5554d857b98088dd`. Exact-head Actions run #840 completed successfully across all five jobs.
- Accessibility PR #76 is closed without merge; its error/not-found implementation is included in PR #68. Do not reopen duplicate work unless the consolidated implementation regresses.

Evidence:
- PR #68: https://github.com/kaustubhdua/Saathi/pull/68
- CI #921: https://github.com/kaustubhdua/Saathi/actions/runs/38777005269
- PR #58: https://github.com/kaustubhdua/Saathi/pull/58
- CI #840: https://github.com/kaustubhdua/Saathi/actions/runs/38720431345
- PR #76: https://github.com/kaustubhdua/Saathi/pull/76

## Newly confirmed review concern

The current proposed enrollment implementation performs household creation and membership insertion as separate REST operations. Concurrent first-time setup for the same Auth identity can leave an unlinked household row if membership creation loses a uniqueness race. This is a data-integrity concern; it does not by itself establish cross-household access.

The atomic-enrollment candidate was published to PR #68 after this report: `66dc2a3`, `8a8df82`, and `35f3557`. A follow-up security hardening commit sets the RPC search path to `pg_catalog` only and adds explicit contract assertions for the lock and grants. The code and proposed SQL are published, but no live database migration was applied. See the 16 October release audit for current evidence and remaining gates.

## Database safety gates (unchanged)

- Read-only checks found six Saathi migration records and eight RLS-enabled Saathi tables in the active Nihdhoom project; `saathi_household_memberships` is absent.
- The separate Saathi Supabase project in `ap-northeast-2` is inactive and its migration-history query timed out. Its history remains unverified.
- PR #58's current migration-history review says the two legacy versions are absent in the active project. The inactive environment is still unresolved. Keep PR #58 draft; do not apply the proposed indexes or run migrations.
- No DDL, migration push, inactive-project restoration, shared non-Saathi database change, or live provider test was performed.

## Release gates still open

1. Publish/review the atomic enrollment fix on the PR #68 branch and require exact-head CI.
2. Run isolated tests for simultaneous enrollment, PIN immutability, recycled phone numbers, two-household isolation, consent revocation races, and RLS/RPC permissions.
3. Verify live Supabase Phone OTP/SMS and server-only secret configuration only with explicit operator authorization.
4. Resolve the five high-severity frontend development-tool-chain advisories or document a reviewed, accepted risk; production-only npm audit currently passes.
5. Complete browser E2E coverage, WCAG 2.2 AA assessment, Lighthouse/Core Web Vitals, production smoke tests, and rollback evidence.
6. Reconcile migration history in every target environment before considering PR #58 or any proposed migration.
7. Keep automatic memory extraction, scheduled reminders, volunteer dispatch, and live phone calls disabled until implemented and verified.
8. Do not configure or deploy Vercel before 2026-10-24.

## Operating rule

PRs remain draft and unmerged. A green CI run establishes only the checks listed in that run, not live identity/provider/database readiness. Re-fetch branch heads and verify CI against the exact current SHA after every new commit.

## Run 21 refresh — 16 October 2026

Latest live GitHub check:
- PR #68 head: `2fee7d7bbb7b999c35cfb376784ec0a160b66851`; still open, draft, not merged.
- Exact-head GitHub Actions run #950 passed all five jobs (frontend, backend, dependency audit, Docker build, Streamlit smoke): https://github.com/kaustubhdua/Saathi/actions/runs/38788953581
- PR #68 reports `mergeable=false` against its recorded base. Resolve branch conflicts against current `main`, then rerun CI on the resulting exact head. Do not force-push or merge as a shortcut.
- PR #58 remains open, draft and unmerged; its mergeability is false and migration-history reconciliation remains a blocker.
- PR #76 remains closed without merging; accessible error/not-found implementation is consolidated in PR #68.

Additional security hardening now in the proposed membership migration:
- `SECURITY DEFINER` enrollment RPC uses a fixed `search_path = pg_catalog` and schema-qualifies application objects.
- Contract tests assert the fixed search path, advisory transaction lock, and explicit execute grants/revocations.
- The membership table and RPC are still proposed only; live schema inspection confirms the active Nihdhoom project does not have `saathi_household_memberships` or the enrollment function. No live DDL was applied.

Release decision remains **NOT PRODUCTION READY**. Passing exact-head CI is necessary but insufficient. Required before release: conflict resolution and new exact-head CI; authorized isolated PostgreSQL execution/security tests; cross-environment migration-history reconciliation; verified live OTP/SMS and household isolation; consent-revocation race tests; provider/Upstash/trusted-IP verification; accessibility/performance and production smoke/rollback evidence. Keep automatic memory extraction, reminder dispatch, volunteer dispatch and live calls disabled. Do not configure/deploy Vercel before 2026-10-24.
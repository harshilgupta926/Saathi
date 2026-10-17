# Saathi Release Audit — Run 24

Date: 2026-10-17 UTC  
Repository: `kaustubhdua/Saathi`  
Candidate inspected: `main` at `27ccef4df93eee899b8107833cf353b20e96c4a9`

This audit records what was verified from GitHub and separates repository checks from external-environment acceptance. It is **not** a production-readiness declaration.

## Verified repository and CI state

- The default branch is `main`; the repository is public and not archived.
- GitHub Actions run [#38974491913](https://github.com/kaustubhdua/Saathi/actions/runs/38974491913) completed successfully on the exact inspected main SHA. All six jobs passed: backend, frontend, dependency audit, Docker build, Streamlit smoke, and database-migration smoke.
- PR [#81](https://github.com/kaustubhdua/Saathi/pull/81) is merged. Its regression tests for rate-limit windows, independent keys, bounded key eviction, and invalid configuration are present on main.
- The codebase includes a production shared Upstash rate-limit implementation in the frontend proxy. This is only operationally ready after the owner configures Upstash and verifies the hosting platform's trusted client-IP header.
- Current main still keeps `DEMO_MODE=true` in the Render Blueprint. This is the safe default until the hosted acceptance path is complete.

## Open reminder PR — not safe to merge yet

PR [#102](https://github.com/kaustubhdua/Saathi/pull/102) proposes scheduled, durable in-app reminders. It is open, reports a dirty merge state against main, and has no check runs for its current head `8a568b63ce181a02d66e633920d0f7b5a7bbe962`. Do not merge or deploy it based on CI from a different commit.

Before reconsidering the PR:

1. Rebase/reconcile its overlapping API, repository, proxy, dashboard and CI changes with current main, then run all checks on the resulting exact head.
2. Validate the proposed SQL migration and acceptance tests on a disposable PostgreSQL database after migration-history reconciliation.
3. Add and test an actual scheduled/background worker deployment definition. The current `render.yaml` declares the API web service only; adding a Python worker module alone does not schedule it.
4. Test notification read authorization and two-household isolation using real, non-production identities.
5. Verify task creation/update/cancellation races, time-zone and daylight-saving transitions, quiet-hour deferral, retry behavior, and duplicate delivery.
6. Keep both feature flags off until all acceptance evidence and owner approval are recorded. The migration is intentionally under `docs/proposed-migrations/` and must not be applied to the shared Nihdhoom project as a shortcut.

## External acceptance still required

These cannot be established by repository CI alone:

- **Deployment timing:** the existing release checklist says not to configure/deploy Vercel before 2026-10-24. As of this audit date (2026-10-17), do not bypass that freeze.
- **Vercel/Render:** after the freeze, set the frontend root directory to `frontend`, configure the server-only backend URL and matching operator token, set exact CORS origins, deploy the approved SHA, and smoke-test the hosted proxy and readiness endpoint.
- **Shared rate limit:** provision Upstash and confirm the platform overwrites the trusted IP header. Verify the rate limit across multiple instances and confirm fail-closed behavior when the store/header is absent.
- **Supabase:** confirm the intended active project and reconcile migration history before any DDL or persistent household feature activation. Never restore/delete another project without explicit owner approval.
- **Identity/privacy:** prove server-side identity-to-household ownership, RLS isolation, OTP/session lifecycle, consent withdrawal, retention/deletion, and concurrent memory revoke/write behavior with isolated test identities.
- **Providers:** capture authorized live evidence for weather and mandi provenance/freshness; real speech STT → tool → Hindi TTS; and, only if advertised, an Exotel call plus verified callback authentication. Keep outbound calls disabled while the callback contract remains unproven.
- **Operations:** perform mobile/keyboard/screen-reader acceptance, WCAG 2.2 AA review, Lighthouse/Core Web Vitals, monitoring/alert setup, backup/restore, and rollback rehearsal. Record redacted evidence and the exact deployed SHA.

## Release decision

**Not production-approved.** Main's current CI is green, but live hosting, Upstash, database identity/RLS, provider round trips, and operational acceptance remain unverified. Keep demo-safe defaults, do not apply proposed migrations to a shared project, and do not describe disabled integrations as working.

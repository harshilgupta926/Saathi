# Saathi Release Feature Ledger

Last verified: 2026-10-15 UTC
Working branch: `fix/household-identity-fail-closed-2026-10-15`
P0/P1 pull request: https://github.com/kaustubhdua/Saathi/pull/57 (merged as `e8a13bdd0022f33707e6a9338d3cc7fcdf039615`)
Household identity fail-closed pull request: https://github.com/kaustubhdua/Saathi/pull/59 (open; CI run #772)
Migration safety/index pull request: https://github.com/kaustubhdua/Saathi/pull/58 (draft; do not merge until other environments are reconciled)
Deployment policy: no Vercel production deployment before 2026-10-24.

Statuses are evidence-based. Database schema readiness does not imply that a user-facing workflow is integrated.

## PASS — verified

- **Shared database identity:** Supabase project `igqgtlmnwssjaoxkkzbm`, named `nihdhoom`, status `ACTIVE_HEALTHY`.
- **Namespaced schema:** eight Saathi-only tables exist: `saathi_conversations`, `saathi_telephony_webhook_events`, `saathi_households`, `saathi_household_memories`, `saathi_pending_tasks`, `saathi_volunteer_cases`, `saathi_calls`, and `saathi_call_events`.
- **Client isolation:** all eight tables have RLS enabled, one explicit deny-all policy for `anon` and `authenticated`, and no SELECT privilege for either role. `service_role` has the required server-side table permissions.
- **Sequence isolation:** anon/authenticated cannot use the three Saathi identity sequences; service_role can.
- **Consent database guard:** synthetic SQL checks confirmed memory writes fail without current memory consent, memory rows are purged on memory-consent revocation, outbound-call consent revocation does not erase unrelated memory consent, and memory cannot be reinserted after revocation.
- **Operational audit privacy:** the conversation adapter sends metadata only and uses `saathi_conversations`; regression tests assert message/transcript/reply fields are absent.
- **Webhook idempotency contract:** the webhook adapter calls `saathi_record_webhook_event`, which atomically claims the event and inserts its `saathi_call_events` ledger row in one transaction. Synthetic SQL verification confirmed first delivery returns new, replay returns duplicate, and both rows are created together.
- **Outbound call safety/persistence:** live calls now require the persisted outbound-consent record for a valid household UUID; a `saathi_calls` row is created before the provider is called, then provider acceptance is recorded. Provider failures mark the row failed; if post-acceptance tracking fails, the API reports `tracking_status: degraded` rather than claiming the call failed.
- **Local runtime smoke harness:** CI starts FastAPI on localhost and checks health, readiness, scheme catalogue and a Hindi conversation; CI also starts the built Next.js app and checks `/dashboard`.
- **Merged P0/P1 CI:** run 770 passed all five jobs on PR #57 head `03483bc3450a08cad161765494758e06c3093cec`; main push run 771 passed on merge commit `e8a13bdd0022f33707e6a9338d3cc7fcdf039615`.
- **Identity fail-closed change:** PR #59 adds backend enforcement and tests rejecting unverified production household IDs; run 772 is the current exact-head CI and must pass before merge.

## PARTIAL — implementation exists, integration remains

- **Frontend API security (PR #57, merged):** dashboard requests use the same-origin allowlisted server proxy; server-side token injection is required in production; the proxy rejects browser-supplied household IDs; readiness fails closed when production auth is missing. This still does not implement end-user login or household ownership.
- **Scheme freshness (PR #57):** static catalogue responses have no live retrieval timestamp and carry reviewed/stale/unknown status; current eligibility and deadlines still require official-portal verification.
- **Mandi freshness (PR #57):** prices with missing/invalid/future arrival dates or observations older than seven days are withheld; live OGD resource/market correctness still requires authorized provider testing.
- **Migration reconciliation (PR #58):** two unprefixed legacy migrations are quarantined outside active discovery, a namespace regression test is added, and a Saathi-only three-index migration is proposed. The PR remains draft. Do not merge/apply until all environments are checked and local/remote migration history is reconciled.

- **Conversation metadata:** backend adapter is wired to the namespaced table; real PostgREST writes require the server-side Nihdhoom secret to be configured in the local/hosted API environment. Unit tests use a mocked HTTP client.
- **Durable webhook deduplication:** backend adapter is wired to the namespaced event ledger. Real signed-provider webhook delivery has not been exercised with provider credentials.
- **Consent/task repositories:** server-only Supabase adapters and regression tests exist. They are not yet wired to authenticated household/task API routes.
- **Household memory, tasks and volunteer cases:** namespaced schema, RLS, indexes and consent protections exist. Consent/task repositories are implemented but not yet wired to authenticated household/task routes; case assignment, retention/deletion UX and authenticated ownership flows are not yet integrated.
- **Call lifecycle:** pre-call and provider-acceptance metadata are wired to `saathi_calls`, but provider callback correlation/terminal-state updates and live provider acceptance remain untested without credentials.
- **Local application:** CI's isolated runner performs localhost runtime smoke tests. This execution container could not clone GitHub directly because outbound DNS resolution failed; no claim is made that the full stack was started in this shell.

## BLOCKED / NOT TESTED

- **Vercel production deployment:** intentionally deferred until 2026-10-24.
- **Production API secret:** never stored in Git or requested in chat; it must be configured as a server-only environment variable on the API host before live persistence is expected.
- **Real telephony/Sarvam/OCR:** live provider acceptance and callback flows remain untested without authorized provider credentials and a public API host.
- **Browser household authentication:** production browser access still needs a verified user-session/household ownership integration. PR #59 rejects unverified household IDs in production; it is a protective denial, not an identity provider.
- **Production SHA and end-to-end journey:** not verified; no new production deployment was made.

## Shared-project findings deliberately left untouched

Supabase security advisors no longer report RLS-enabled/no-policy findings for Saathi tables. The remaining findings concern existing Nihdhoom Telegram tables and shared SECURITY DEFINER functions. They are not changed here because Nihdhoom is shared with unrelated applications and Saathi work must remain inside `saathi_*` objects.

## Next actions

1. PR #57 is merged and main CI run #771 is green. Wait for exact-head CI run #772 on PR #59 before reviewing/merging the fail-closed household-identity guard.
2. Keep PR #58 draft until migration history is reconciled in every relevant environment; do not run live DDL before approval.
3. Implement verified user sessions and identity-to-household ownership before enabling household memory/task routes; then test cross-household denial, consent grant/revocation, memory deletion, retention and task authorization.
4. Run real Open-Meteo/OGD and Sarvam provider journeys with approved credentials; verify provenance, date selection, STT → tool → TTS, failure states and measured latency.
5. Correlate signed provider callbacks to `saathi_calls`, update terminal call states idempotently, and prove the public WSS round trip if phone AI will be advertised.
6. Add a reviewed frontend lockfile and `npm ci`; finish browser/mobile, keyboard/screen-reader/reduced-motion, Lighthouse/Core Web Vitals and release rollback evidence.
7. Keep Vercel deployment/configuration deferred until 2026-10-24; then verify the exact production URL, deployed SHA, configuration, smoke tests and rollback procedure.

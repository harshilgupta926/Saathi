# Saathi Release Feature Ledger

Last verified: 2026-10-14 UTC
Working branch: `fix/nihdhoom-saathi-persistence`
Pull request: https://github.com/kaustubhdua/Saathi/pull/56
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
- **Local runtime smoke harness:** CI starts FastAPI on localhost and checks health, readiness, scheme catalogue and a Hindi conversation; CI also starts the built Next.js app and checks `/dashboard`.
- **Previous full CI:** run 702 passed all five jobs, including backend tests, frontend lint/type/build, dependency audits, Streamlit smoke and Docker build. That run predates the newest repository-adapter and consent-locking commits; see the current CI run before treating those changes as validated.

## PARTIAL — implementation exists, integration remains

- **Conversation metadata:** backend adapter is wired to the namespaced table; real PostgREST writes require the server-side Nihdhoom secret to be configured in the local/hosted API environment. Unit tests use a mocked HTTP client.
- **Durable webhook deduplication:** backend adapter is wired to the namespaced event ledger. Real signed-provider webhook delivery has not been exercised with provider credentials.
- **Consent/task repositories:** server-only Supabase adapters and regression tests exist. They are not yet wired to authenticated household/task API routes.
- **Household memory, tasks, volunteer cases and calls:** namespaced schema, RLS, indexes and consent protections exist. Consent/task repositories are implemented but not yet wired to authenticated household/task routes; call lifecycle records in `saathi_calls`, case assignment, retention/deletion UX and authenticated ownership flows are not yet integrated.
- **Local application:** CI's isolated runner performs localhost runtime smoke tests. This execution container could not clone GitHub directly because outbound DNS resolution failed; no claim is made that the full stack was started in this shell.

## BLOCKED / NOT TESTED

- **Vercel production deployment:** intentionally deferred until 2026-10-24.
- **Production API secret:** never stored in Git or requested in chat; it must be configured as a server-only environment variable on the API host before live persistence is expected.
- **Real telephony/Sarvam/OCR:** live provider acceptance and callback flows remain untested without authorized provider credentials and a public API host.
- **Browser household authentication:** production browser access still needs verified user-session/household ownership integration before exposing memory/task routes.
- **Production SHA and end-to-end journey:** not verified; no new production deployment was made.

## Shared-project findings deliberately left untouched

Supabase security advisors no longer report RLS-enabled/no-policy findings for Saathi tables. The remaining findings concern existing Nihdhoom Telegram tables and shared SECURITY DEFINER functions. They are not changed here because Nihdhoom is shared with unrelated applications and Saathi work must remain inside `saathi_*` objects.

## Next actions

1. Wait for the latest CI run on the final branch head (including the atomic webhook RPC and idempotent task adapters); fix every regression before merge.
2. Wire consent/task repositories behind authenticated server-side household ownership and add tests for cross-household denial and consent revocation.
3. Integrate durable call records with provider callbacks and verify idempotency before the 24 October deployment window.

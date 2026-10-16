# Server-side API proxy

The dashboard uses same-origin `/backend/*` routes. The Next.js Node route forwards only allowlisted readiness, agent-text, voice-turn, purpose-specific consent, household task and user-entered memory endpoints. It injects `X-Saathi-API-Key` from server-only `SAATHI_API_AUTH_TOKEN` and adds verified household headers only after server-side OTP + household PIN checks.

## Required configuration

- `BACKEND_API_URL`: HTTPS origin of FastAPI in deployed environments.
- `SAATHI_API_AUTH_TOKEN`: high-entropy value of at least 32 characters matching backend `API_AUTH_TOKEN`.
- Keep both variables server-side. Never expose the token through `NEXT_PUBLIC_*`.
- A localhost fallback exists only when `NODE_ENV=development`.

## Boundaries

- Only `GET /health/ready`, `GET /health/live`, `POST /api/v1/agent`, `POST /api/v1/voice/turn`, authenticated `GET/POST /api/v1/household/consent`, authenticated `GET/POST /api/v1/household/tasks`, authenticated `POST /api/v1/household/tasks/status`, authenticated `GET/POST /api/v1/household/memories`, and authenticated `POST /api/v1/household/memories/delete` are exposed.
- The proxy rejects browser-supplied household identifiers, checks mutation origins when present, bounds request-body size and read time, rejects redirects, uses no-store responses, and includes a best-effort per-process rate limit.
- Text requests are limited to 64 KiB; voice uploads are limited to 10 MiB. Upstream calls have bounded timeouts.
- Production requires `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`, and `SAATHI_TRUSTED_CLIENT_IP_HEADER`. The configured URL must be an HTTPS `*.upstash.io` origin with no custom port, credentials, path, query or fragment. The chosen header must be a single IP address and must be documented/configured by the hosting platform to be overwritten; the app does not trust `X-Forwarded-For` chains by default.
- Production uses an atomic fixed-window Redis Lua counter. Its key is an HMAC-SHA-256 digest of the method/route/IP tuple, not the raw IP. Missing/malformed configuration, unknown trusted IPs, Redis errors, and invalid Redis responses fail closed before the backend is called. A Redis outage therefore affects availability by design; configure and test the shared store before enabling production traffic.
- Non-production uses a process-local limiter for development/testing only. It validates IP literals and caps bucket storage at 2,000 entries under high-cardinality traffic. This local fallback is not distributed protection and must never be treated as the production abuse boundary.
- Phone OTP login uses Supabase Auth SSR cookies. For signed-in users, the server verifies the Supabase user, requires a confirmed E.164 phone, then resolves the household through `saathi_household_memberships.auth_user_id`. A phone number alone never grants access, avoiding takeover if a number is recycled. The membership migration remains proposed outside active migration discovery until PR #58 is reconciled.
- The proxy injects `X-Saathi-Verified-Identity` and `X-Saathi-Verified-Household` only after server-side verification; the backend validates both UUIDs and rejects client-supplied household IDs.
- The consent API exposes only memory and outbound-call purpose booleans. Both start false; revoking memory relies on the existing database trigger to purge stored memory.
- Household task, consent and user-entered memory APIs are exposed only after server-side identity and household PIN verification; they fail closed while the membership migration or required secrets are unavailable. General conversation and voice remain usable without an account, but no household context is attached unless the user has completed verification.
- Outbound-call operations remain unavailable through the public proxy. Scheduled reminders, automatic follow-up delivery and volunteer assignment are not enabled.
- Production readiness reports `not_ready` when required API operator authentication is missing.

## Verification

CI runs `node --test tests/*.test.mjs` plus lint, TypeScript, the Next.js build and a local dashboard smoke check. The proxy tests stub the Redis limiter and API upstream; they do not prove live provider or deployment behavior. These tests stub the upstream; they do not prove live provider or deployment behavior.

## Household identity fail-closed behavior

The backend rejects a client-supplied household identifier on text and voice interaction routes outside local demo mode. A household UUID is not an identity credential. PR #68 adds a Supabase Auth OTP + household PIN identity-to-household flow and server-side ownership check, but the required `saathi_household_memberships` table is still only a proposed migration. Household-specific routes therefore fail closed until PR #58's migration-history reconciliation is complete, the membership schema is reviewed/applied safely, and live identity/isolation tests pass. Do not treat this draft branch as production-enabled.


## Shared limiter verification

The automated proxy tests stub Redis and the API separately. They cover missing configuration, rejected hosts/ports, malformed client IPs, Redis outage/invalid counter response, and the over-limit path. They do not prove that a production Upstash database exists, that the hosting proxy overwrites the selected header, or that live traffic is correctly limited. Verify those conditions in the deployment environment before switching out of demo mode.


## Additional server-only configuration

- `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (or the existing public anon key) are public Auth client configuration.
- `SUPABASE_URL` and `SUPABASE_SECRET_KEY` are server-only. The secret key must never use a `NEXT_PUBLIC_*` name and must never be serialized to a browser response.
- Enable Supabase Phone Auth and configure SMS delivery in the project dashboard. This repository cannot provision the provider or prove delivery.
- Production OTP/PIN requests use atomic Upstash Redis counters and require a configured trusted single-IP header. The process-local limiter is development/test fallback only. Supabase Auth's own rate limits and SMS provider controls remain additional defenses.


## Household workflow routes

Task reads and updates are scoped to the server-verified household; idempotency-conflict recovery must also filter by household and reject any mismatched response. Memory reads/writes require persisted memory consent, and the database guard independently rejects writes that race with revocation. Memory values are stored only when explicitly submitted by the user; automatic conversation extraction is not enabled. Reminder dispatch and volunteer delivery remain unavailable and must not be presented as active.

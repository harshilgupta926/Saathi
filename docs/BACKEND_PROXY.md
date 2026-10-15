# Server-side API proxy

The dashboard uses same-origin `/backend/*` routes. The Next.js Node route forwards only the allowlisted readiness, agent-text and voice-turn endpoints and injects `X-Saathi-API-Key` from server-only `SAATHI_API_AUTH_TOKEN`.

## Required configuration

- `BACKEND_API_URL`: HTTPS origin of FastAPI in deployed environments.
- `SAATHI_API_AUTH_TOKEN`: high-entropy value of at least 32 characters matching backend `API_AUTH_TOKEN`.
- Keep both variables server-side. Never expose the token through `NEXT_PUBLIC_*`.
- A localhost fallback exists only when `NODE_ENV=development`.

## Boundaries

- Only `GET /health/ready`, `GET /health/live`, `POST /api/v1/agent` and `POST /api/v1/voice/turn` are exposed.
- The proxy rejects browser-supplied household identifiers, checks mutation origins when present, bounds request-body size and read time, rejects redirects, uses no-store responses, and includes a best-effort per-process rate limit.
- Text requests are limited to 64 KiB; voice uploads are limited to 10 MiB. Upstream calls have bounded timeouts.
- Production requires `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`, and `SAATHI_TRUSTED_CLIENT_IP_HEADER`. The configured URL must be an HTTPS `*.upstash.io` origin with no custom port, credentials, path, query or fragment. The chosen header must be a single IP address and must be documented/configured by the hosting platform to be overwritten; the app does not trust `X-Forwarded-For` chains by default.
- Production uses an atomic fixed-window Redis Lua counter. Its key is an HMAC-SHA-256 digest of the method/route/IP tuple, not the raw IP. Missing/malformed configuration, unknown trusted IPs, Redis errors, and invalid Redis responses fail closed before the backend is called. A Redis outage therefore affects availability by design; configure and test the shared store before enabling production traffic.
- Non-production uses a process-local limiter for development/testing only. It validates IP literals and caps bucket storage at 2,000 entries under high-cardinality traffic. This local fallback is not distributed protection and must never be treated as the production abuse boundary.
- This proxy does not implement login, verified household identity, consent, persistent memory, task APIs or outbound calls. Those routes remain unavailable until end-to-end authorization is implemented.
- Production readiness reports `not_ready` when required API operator authentication is missing.

## Verification

CI runs `node --test tests/*.test.mjs` plus lint, TypeScript, the Next.js build and a local dashboard smoke check. The proxy tests stub the Redis limiter and API upstream; they do not prove live provider or deployment behavior. These tests stub the upstream; they do not prove live provider or deployment behavior.

## Household identity fail-closed behavior

The backend rejects a client-supplied household identifier on text and voice interaction routes outside local demo mode. A household UUID is not an identity credential. Until a verified end-user identity provider and identity-to-household ownership check are integrated, production requests must omit household IDs; household-specific memory, tasks and consent APIs must not be exposed through the public proxy. This intentionally blocks household-personalized production workflows rather than silently trusting a client-supplied UUID.


## Shared limiter verification

The automated proxy tests stub Redis and the API separately. They cover missing configuration, rejected hosts/ports, malformed client IPs, Redis outage/invalid counter response, and the over-limit path. They do not prove that a production Upstash database exists, that the hosting proxy overwrites the selected header, or that live traffic is correctly limited. Verify those conditions in the deployment environment before switching out of demo mode.

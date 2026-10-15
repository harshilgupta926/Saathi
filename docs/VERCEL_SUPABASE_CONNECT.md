# Vercel + FastAPI + Supabase connection

## Architecture

- **Vercel** hosts the Next.js frontend from the `frontend/` directory.
- The browser calls same-origin `/backend/*` paths. A server-side Next.js route allowlists supported public interactions and injects the API operator token; do not use an unauthenticated rewrite or expose the token to browser code.
- **FastAPI** stays on the Docker web service (Render or another ASGI host). It talks to Supabase server-side using `SUPABASE_URL` and `SUPABASE_SECRET_KEY`.
- **Supabase** uses the existing Nihdhoom project for shared infrastructure. Saathi data is kept in namespaced tables `public.saathi_conversations` and `public.saathi_telephony_webhook_events`; these tables have RLS enabled and deny browser-role access.

Vercel does not run this Docker FastAPI service just because the frontend is deployed there. Keep the API on Render (or another ASGI host) and point Vercel at its public HTTPS origin.

## Vercel project settings

Import `kaustubhdua/Saathi` at https://vercel.com/new.

- Framework preset: **Next.js**
- Root Directory: **`frontend`**
- Install/build commands: use defaults from `frontend/package.json`
- Production branch: `main`

Set this environment variable for **Production, Preview and Development** as appropriate:

| Variable | Value |
| --- | --- |
| `BACKEND_API_URL` | Public HTTPS origin of the deployed FastAPI service, e.g. `https://YOUR-SERVICE.onrender.com` |
| `SAATHI_API_AUTH_TOKEN` | High-entropy server-only token matching backend `API_AUTH_TOKEN` (at least 32 characters) |

Do not include a trailing slash. The frontend uses `/backend` in production; the server-side route injects `X-Saathi-API-Key`. Production readiness fails when the API operator token is missing. Redeploy after changing environment variables.

For local development, set `BACKEND_API_URL=http://localhost:8000` in `frontend/.env.local` and run FastAPI on port 8000. The token remains server-only; a local non-production demo may omit it.

## FastAPI service environment

In the API service's environment settings, set:

| Variable | Value |
| --- | --- |
| `SUPABASE_URL` | `https://igqgtlmnwssjaoxkkzbm.supabase.co` (existing Nihdhoom project) |
| `SUPABASE_SECRET_KEY` | Server-side secret/service-role key from the Nihdhoom project's Supabase API Keys settings |
| `CORS_ORIGINS` | Your Vercel production URL (and any required preview URL, comma-separated) |
| `DEMO_MODE` | `true` while validating |

Never put `SUPABASE_SECRET_KEY` in Vercel variables prefixed with `NEXT_PUBLIC_`, frontend source, or browser storage. Do not use the publishable/anon key for server-side writes. Do not paste the secret key into chat or commit it to Git.

The namespaced database migration is applied to the shared Nihdhoom project. The API's minimal audit write is best-effort: core answers continue if Supabase is unavailable, while the server logs a non-sensitive failure status. Durable webhook idempotency fails closed when the database is unavailable.

## Smoke test after local setup and deployment

1. Open `/backend/health/ready`. Expect JSON with `status: "ready"` only when required auth is configured; production without the operator token returns `status: "not_ready"`.
2. Open `/dashboard`; the header should show **API ready**.
3. Submit a harmless test question. Confirm a response appears.
4. In Supabase Table Editor, inspect `public.saathi_conversations`. A metadata row should appear when the server secret key is configured correctly. It must contain no raw user message or assistant response.
5. Check API logs for `supabase_audit_write_failed`; if present, verify the service key, project URL, table schema and service-role permissions.
6. Send a signed test webhook twice with the same provider event ID in a non-production environment. The first request should be accepted and the second identified as a duplicate.

Keep demo mode enabled and do not make outbound calls during smoke testing.

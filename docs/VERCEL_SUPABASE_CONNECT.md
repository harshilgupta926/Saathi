# Vercel + FastAPI + Supabase connection

## Architecture

- **Vercel** hosts the Next.js frontend from the `frontend/` directory.
- The browser calls same-origin `/backend/*` paths. Next.js rewrites these requests to the FastAPI service, avoiding browser CORS configuration for normal API calls.
- **FastAPI** stays on the existing Docker web service (Render). It talks to Supabase server-side using `SUPABASE_URL` and `SUPABASE_SECRET_KEY`.
- **Supabase** stores the migrated tables. The API writes only minimal operational conversation metadata; it does not persist raw prompts, transcripts or model replies.

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

Do not include a trailing slash. The frontend automatically uses `/backend` in production and the Next.js rewrite forwards requests to this origin. Redeploy after changing environment variables.

For local development, keep `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local` and run FastAPI on port 8000.

## FastAPI service environment

In the Render service's Environment page, set:

| Variable | Value |
| --- | --- |
| `SUPABASE_URL` | `https://gqbrllxufyeqbuuxhnjd.supabase.co` |
| `SUPABASE_SECRET_KEY` | The project's server-side Supabase secret/service-role key, copied from Supabase Project Settings → API Keys |
| `CORS_ORIGINS` | Your Vercel production URL (and any required preview URL, comma-separated) |
| `DEMO_MODE` | `true` while validating |

Never put `SUPABASE_SECRET_KEY` in Vercel variables prefixed with `NEXT_PUBLIC_`, frontend source, or browser storage. Do not use the publishable/anon key for server-side writes. Do not paste the secret key into chat or commit it to Git.

The database migrations are already applied to the connected Supabase project. The API's minimal audit write is best-effort: core answers continue if Supabase is unavailable, while the server logs a non-sensitive failure status. This is not a replacement for persistent household memory or callback dispatch, which remain separate implementation work.

## Smoke test after setting environment variables

1. Open the Vercel deployment and visit `/backend/health/ready`. Expect JSON with `status: "ready"`.
2. Open `/dashboard`; the header should show **API ready**.
3. Submit a harmless test question. Confirm a response appears.
4. In Supabase Table Editor, inspect `public.conversations`. A metadata row should appear if the server secret key is configured correctly. It should contain no raw user message or assistant response.
5. Check Render logs for `supabase_audit_write_failed`; if present, verify the service key, project URL, table schema and service-role permissions.

Keep demo mode enabled and do not make outbound calls during the smoke test.

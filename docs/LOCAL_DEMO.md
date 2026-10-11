# Local product run

Saathi can be run without any paid provider credentials.

## Fastest path

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend, in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000/dashboard`.

With `DEMO_MODE=true`:

- text requests work against deterministic demo tools;
- weather and mandi responses are explicitly labelled as demo data;
- browser-native speech recognition/synthesis can provide a local voice preview where supported;
- provider-backed Sarvam STT/TTS is never claimed as live.

## Docker

From the repository root:

```bash
docker compose up --build
```

Then open `http://localhost:3000/dashboard`.

## Moving from demo to live

Set `DEMO_MODE=false` only after the required provider credentials are configured. Follow `docs/DEPLOYMENT.md` and `docs/REAL_PROVIDER_RUNBOOK.md`.

# Local product run

Saathi can be run without any paid provider credentials. The default backend speech path is local Vosk STT plus eSpeak NG TTS; it does not silently fall back to a hosted provider.

## Offline Hindi speech model

The application code does not download speech models at runtime. Download the official [Vosk small Hindi model](https://alphacephei.com/vosk/models/vosk-model-small-hi-0.22.zip) and extract it so this directory exists:

```text
models/vosk-model-small-hi-0.22/am/
```

The official Vosk model list marks `vosk-model-small-hi-0.22` Apache-2.0 and reports word-error-rate results of 20.89 (IITM Challenge) and 24.72 (MUCS Challenge). Those are upstream benchmark figures, not Saathi-specific Hindi/Hinglish/Haryanvi acceptance results. See [Vosk model licenses and metrics](https://alphacephei.com/vosk/models). eSpeak NG supplies offline speech synthesis; its voice is intentionally robotic compared with neural hosted TTS. Review GPL-3.0 obligations for the installed eSpeak NG distribution before redistributing an image.

Docker Compose mounts `./models/vosk-model-small-hi-0.22` read-only at `/models/vosk-model-small-hi-0.22`. Override `VOSK_MODEL_HOST_PATH` if your extracted model lives elsewhere. If the model is missing, `/health/ready` reports speech as unavailable and the audio endpoint returns an explicit error.

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
- the backend uses Vosk/eSpeak NG only when the local Hindi model and system binaries are installed;
- provider-backed Sarvam STT/TTS is never claimed as live or used as a silent fallback.

## Docker

From the repository root:

```bash
docker compose up --build
```

Then open `http://localhost:3000/dashboard`.

## Moving from demo to live

Set `DEMO_MODE=false` only after the required provider credentials are configured. Follow `docs/DEPLOYMENT.md` and `docs/REAL_PROVIDER_RUNBOOK.md`.

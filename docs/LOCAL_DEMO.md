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

## Full local reasoning (no hosted AI API key)

The base Compose demo keeps the deterministic demo path lightweight. To run the actual local Ollama model as well, use the override file:

```bash
docker compose -f docker-compose.yml -f docker-compose.local-ai.yml up --build
```

This starts the pinned Ollama container, pulls `qwen2.5:7b` into the persistent `ollama-data` volume, and points the backend at the internal Ollama service. The first run downloads several gigabytes and needs sufficient disk space and RAM; do not use this mode on a low-memory host. The Ollama port is not published to the host by this Compose override. If model pulling fails, Compose does not start the backend in this full-local mode rather than silently using a hosted provider.

For a host-installed Ollama instance instead, run `ollama pull qwen2.5:7b`, set `LLM_PROVIDER=ollama` and `OLLAMA_BASE_URL` to the host service address appropriate for your environment. The model's upstream variant terms and hardware fit must be reviewed before redistribution or deployment.

## Moving from demo to live

Set `DEMO_MODE=false` only after the required provider credentials are configured. Follow `docs/DEPLOYMENT.md` and `docs/REAL_PROVIDER_RUNBOOK.md`.


## Real local-model acceptance probe

After the model has finished downloading and Ollama is reachable, run this opt-in check from the repository root:

```bash
OLLAMA_BASE_URL=http://127.0.0.1:11434 LLM_MODEL=qwen2.5:7b \
  python backend/scripts/smoke_local_ollama.py
```

The probe sends one weather-intent prompt to the actual local model, records selected tool and elapsed milliseconds, and exits non-zero unless the model selects the declared `get_weather` tool. It does not use mocks or fall back to a hosted provider. Repeat on each target hardware class and retain the JSON output with the model tag, machine/RAM details, and p50/p95 results from a larger evaluation set before claiming acceptable latency. A single pass is only a smoke test, not a Hindi/Hinglish/Haryanvi quality benchmark.

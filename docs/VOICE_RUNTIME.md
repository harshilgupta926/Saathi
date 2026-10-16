# Saathi voice runtime

## Browser voice loop

The /api/v1/voice/turn endpoint accepts a short browser-recorded audio file and returns:

1. transcript
2. deterministic specialist intent
3. verified tool result when available
4. source provenance
5. optional synthesized Hindi audio
6. escalation metadata
7. correlation ID

The frontend microphone control uses this endpoint. The default backend path is local Vosk Hindi STT plus eSpeak NG TTS, with ffmpeg conversion for WebM/WAV input. It uses no hosted speech credentials and never silently falls back to Sarvam. The Vosk model must be downloaded separately and mounted at `VOSK_MODEL_PATH`; readiness reports speech unavailable until the model and binaries exist. Browser-native speech remains a separate optional browser path and may depend on OS/browser services.

## Phone voice loop

The repository exposes /api/v1/telephony/stream as a FastAPI WebSocket endpoint for Exotel AgentStream. It accepts Exotel connected, start, media and stop events and sends bidirectional media frames containing raw mono Linear16 PCM.

The endpoint now supports two explicit modes. The default bounded-turn adapter remains available as a safe fallback. When `SARVAM_REALTIME_STT_ENABLED=true`, Exotel PCM is streamed to Sarvam Realtime STT with server VAD and final transcript events; replies are synthesized through Sarvam streaming TTS and streamed back to Exotel. Barge-in cancels the active response and sends Exotel `clear`.

The realtime path is implemented but provider/deployment verification is still required before calling it a live production phone agent. Exotel AgentStream sends raw 16-bit mono Linear16 PCM at 8/16/24 kHz; the realtime Sarvam STT path currently accepts 8/16 kHz and the TTS path emits Linear16 at the negotiated rate.

Do not claim live phone AI until a real Exotel call has completed the complete audio round trip on a deployed public wss:// endpoint.

## Provider configuration

- STT: local Vosk Hindi model by default; optional Sarvam Saaras v4 only when `SPEECH_PROVIDER=sarvam`
- TTS: local eSpeak NG by default; optional Sarvam Bulbul v3 only when `SPEECH_PROVIDER=sarvam`
- Hindi code: hi-IN
- Browser audio: WebM upload
- Phone audio: raw Linear16 PCM
- Hosted provider key: server-side only, optional
- Local model: Vosk Hindi small model, Apache-2.0; model files are operator-installed and not stored in Git
- Local TTS: eSpeak NG, GPL-3.0 distribution obligations apply
- Offline acceptance: real audio round trip, latency and Hindi/Hinglish/Haryanvi benchmarks are still required

Sarvam documents linear16 output and 8 kHz telephony sample rates for voice pipelines.

## Safety boundary

The voice endpoint does not grant the model authority to invent prices, weather, eligibility, application status or deadlines. Those answers must come from deterministic rules or a verified provider tool.

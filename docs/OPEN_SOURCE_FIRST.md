# Open-source-first, API-key-free core

Saathi's core must run without paid hosted AI credentials. This policy applies to the default developer setup and must remain true in CI.

## Default runtime

- **Reasoning/tool selection:** Ollama running locally with an installed open-weight model (default: `qwen2.5:7b` (Apache-2.0 variant; verify the exact model manifest/tag at adoption time)). Tool calls are proposals only; deterministic intent classification, capability policy, argument validation and source adapters remain authoritative.
- **Speech in browser:** browser-native speech recognition/synthesis is a convenience fallback, not an offline guarantee. Browser speech engines may use network services depending on browser/OS. Label this clearly in UI.
- **Speech fully offline:** use a locally installed Whisper/whisper.cpp or Vosk model for STT and a locally installed Piper voice for TTS after verifying Hindi/Hinglish quality and each model/voice license. Do not claim this is implemented until the adapters are wired and tested.
- **OCR:** `POST /api/v1/documents/ocr` is wired to a local Tesseract subprocess. It accepts bounded PNG/JPEG/WebP/TIFF images only, checks image signatures, enforces a processing timeout, never stores/uploads the image, returns word-confidence metadata, and flags low-confidence output for human review. The Dockerfiles install Tesseract plus Hindi/English language packs. Real-image accuracy, real binary execution, PDF OCR, and farmer-document benchmarks remain unverified; this is not yet a fully accepted document-understanding workflow.
- **Weather:** Open-Meteo adapter is keyless but needs internet for fresh forecasts. A cached result must show its retrieval time and stale status.
- **Mandi data:** OGD/AGMARKNET access may require a data.gov.in key depending on endpoint/quota. The no-key baseline must gracefully say live mandi prices are unavailable and must never substitute simulated prices without a visible demo label.
- **Scheme information:** use a versioned, source-linked local catalogue and official government links. Display review date and require official confirmation for eligibility and submissions.
- **Persistence and reminders:** a local/self-hosted PostgreSQL deployment can avoid a hosted database vendor API key, but durable consent, household isolation, idempotency, scheduling and delivery tests are still mandatory before enabling household workflows.
- **Telephony:** outbound phone calls are explicitly optional and disabled by default. Browser audio/in-app reminders are the no-key baseline; carrier calling cannot honestly be promised without a compatible provider or user-owned telephony infrastructure.

## Model license and hardware gate

The default is `qwen2.5:7b`, selected instead of the Qwen2.5 3B variant because the upstream Qwen2.5 licensing matrix identifies the 7B variant as Apache-2.0 while the 3B variant has different terms. The model weights and any quantized Ollama artifact must be checked against the exact upstream model card/manifest before redistribution. Apache-2.0 applies to the model variant, not automatically to the whole application or any voice/model assets. The 7B model also requires materially more memory and inference time than a 3B model; measure on the intended host before release. Do not claim that model download, license review of every dependency, or Hindi/Haryanvi quality benchmarking has been completed merely because this default is configured.

## Local setup

1. Install Ollama from its official distribution for your OS. For local development outside Docker, install Tesseract and its `hin` and `eng` language packs; the repository Dockerfiles include them.
2. Pull a model locally, for example `ollama pull qwen2.5:7b`.
3. Set `LLM_PROVIDER=ollama`, `LLM_MODEL=qwen2.5:7b`, and `OLLAMA_BASE_URL=http://127.0.0.1:11434`. Set `DEMO_MODE=false` to activate the local model. `DEMO_MODE=true` deliberately bypasses model/network calls so the synthetic demo and CI remain deterministic.
4. Keep `DEMO_MODE=true` for synthetic data and demonstrations. For live public data, explicitly configure live mode and verify each source adapter; do not enable household features merely to make the demo work.
5. If the local model is unavailable, Saathi must continue using deterministic routing where possible and clearly report optional reasoning unavailable. It must not silently fall back to a hosted model.

## Release gates

- CI proves default configuration does not require Gemini, OpenAI, Sarvam, Bhashini, Exotel or Supabase credentials.
- Tests cover Ollama success, no tool call, malformed tool arguments, timeout/connection failure and unsupported tool names.
- Tests prove model output cannot bypass deterministic intent/tool policy, change the caller's household identity, or invent factual source provenance.
- Test no-network mode separately from live public-data mode.
- Verify model and voice licenses, redistribution terms, hardware/latency budget, Hindi/Hinglish quality and accessibility.
- Run local OCR against representative real Hindi/English images, report character/word error rate, test timeout/invalid-image handling, and document that PDFs are not accepted by the current OCR endpoint.
- Do not mark local OCR/STT/TTS, durable reminders, live mandi data, or telephony as complete until implementation and acceptance evidence exists.

## Cost and privacy notes

“No API keys” does not mean “no infrastructure cost.” Local inference consumes device/server CPU, RAM, storage and sometimes GPU resources. Public-data adapters still need network access. Keep sensitive audio and documents local by default, avoid logging raw prompts/uploads, and never ship secrets in frontend environment variables.

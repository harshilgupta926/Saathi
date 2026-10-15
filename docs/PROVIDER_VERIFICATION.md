# Live provider verification plan

Last reviewed: 2026-10-15

A configured adapter is not a verified integration. Keep demo mode on and do not advertise a provider path as live until the following evidence is attached to the release candidate.

## Exotel callbacks and phone AI

References:
- [Exotel outbound call API and StatusCallback fields](https://developer.exotel.com/api/outgoing-call-to-connect-number-to-a-call-flow)
- [Exotel status callback reliability](https://docs.exotel.com/voice-apis/statuscallback-reliability-expected-latency-retry-logic-and-handling-missed-callbacks?open=browser)

The documented callback fields include CallSid, Status, RecordingUrl, and DateUpdated; statuses can include completed, failed, busy, and no-answer. The payload may be form-encoded. The app now parses JSON and form payloads, uses the signed raw body for idempotency, and applies monotonic call-state transitions to the Saathi call/event records.

**Unresolved authentication contract:** the Saathi webhook currently requires X-Saathi-Signature, an HMAC over the exact raw body. The referenced Exotel status-callback docs do not establish that Exotel sends this custom header. Do not set TELEPHONY_CALLBACK_SIGNATURE_VERIFIED=true until an actual provider sandbox callback proves the deployed endpoint authenticates requests reliably, without relying on an unsigned ID header. Live outbound calls fail closed while this flag is false.

Required sandbox evidence:
- One real outbound call with persisted purpose-specific consent.
- Captured redacted callback headers/content type and payload shape; never save phone numbers or recording URLs in public logs.
- Signature verification using the actual provider/gateway contract.
- Duplicate callback and retry-after-temporary-failure tests.
- Final call state and event ledger linked by internal call UUID.
- Reconnect/interruption/barge-in test for the public WSS audio path if real-time phone AI is advertised.

## Sarvam browser speech and document AI

References:
- [Sarvam speech-to-text REST API](https://docs.sarvam.ai/api-reference/speech-to-text/transcribe)
- [Sarvam text-to-speech REST API](https://docs.sarvam.ai/api/api-guides-tutorials/text-to-speech/rest-api)
- [Sarvam model API introduction](https://docs.sarvam.ai/api-reference/introduction)

Required evidence:
- Test with a real server-side API key; never put it in a browser bundle or repository.
- Use real microphone audio, not an empty MediaRecorder blob or canned transcript.
- Verify Hindi and Hinglish transcription, intent/tool routing, grounded answer, and generated audio playback.
- Record request IDs, redacted error classes, p50/p95 end-to-end latency, and failure behavior.
- For document AI, verify the actual endpoint/request contract, job lifecycle, field-level provenance/confidence, safe file retention and deletion.

## Government mandi data

Reference:
- [OGD India current daily market prices (Mandi)](https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi)

Required evidence:
- Validate commodity, state, district, market, variety/grade if present, price unit, and record observation date.
- Never substitute the time Saathi fetched a response for the market observation date.
- Withhold missing, invalid, future-dated or older-than-seven-day records from current-price claims.
- Save a redacted test fixture with the actual response schema and record date, plus a regression test for selection ambiguity.

## Weather

Reference:
- [Open-Meteo API documentation](https://open-meteo.com/en/docs)

Required evidence:
- Use an explicit user-provided or verified location; do not infer location from IP or a hardcoded demo district.
- Check units, timezone, forecast/current observation time, provider errors and unavailable-location behavior.
- Verify the returned source and retrieval timestamp in the UI.

## Credentials and evidence policy

- Store credentials only in the deployment platform's server-side secret manager.
- No provider live-test result is inferred from CI stubs or a green Docker build.
- Redact phone numbers, transcripts, API keys, callback secrets, and signed payloads from logs and evidence.
- Keep all persistence changes scoped to saathi_* objects in Nihdhoom.

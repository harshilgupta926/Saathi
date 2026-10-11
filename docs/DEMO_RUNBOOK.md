# Saathi demo runbook

## Golden path

1. Open the operator dashboard at `/dashboard`.
2. Start **Judge Mode → Start golden demo** to show the intended request → intent → tool → evidence → escalation chain.
3. Switch to the real request panel and ask in Hindi/Hinglish: “गेहूं का मंडी भाव क्या है?”
4. Show the farming intent, specialist capability, tool result and provenance.
5. Ask: “अगले 24 घंटे में बारिश की संभावना कितनी है?”
6. Show the weather result and retrieval metadata.
7. Ask a scheme question such as: “PM Kisan ke liye kya chahiye?”
8. Ask for a human: “मुझे किसी इंसान से बात करनी है” and show the escalation boundary.
9. If Sarvam credentials are configured, optionally record a browser voice turn and play the returned TTS audio.

## Streamlit judge path

- Deploy `streamlit_app/app.py` for the standalone judge-friendly experience.
- Start in `DEMO_MODE=true` unless the real provider path has already been exercised.
- Use the Operator view to expose intent, capability, confidence, latency and provenance.
- Keep simulated data explicitly labelled.
- Add live provider secrets only for capabilities that have been verified end-to-end.

## Truthfulness rules

- Never call simulated data live data.
- Never claim a real phone call unless the telephony provider is configured and the call was actually placed.
- Never claim an application was submitted unless the official integration confirms it.
- Never expose secrets in screenshots or recordings.

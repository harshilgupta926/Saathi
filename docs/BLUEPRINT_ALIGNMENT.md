# Saathi blueprint alignment and implementation gates

Updated: 2026-10-10

## Product promise

Saathi is a voice-first Hindi/Hinglish assistance prototype with a grounded tool layer and an operator escalation boundary. The long-term blueprint adds consented household memory, durable tasks, scheduled callbacks and volunteer case management. Those later workflows must not be presented as live until the full persistence-to-provider path is tested.

## Architecture mapping

| Blueprint component | Current implementation | Status / gate |
|---|---|---|
| Web/operator interface | Next.js dashboard and Streamlit judge app | Implemented; test the exact deployed build |
| FastAPI orchestrator | Backend intent/orchestration and allow-listed tool boundary | Implemented; validate live provider path |
| Hindi/Hinglish speech | Sarvam browser STT/TTS; realtime/streaming transport adapters | Adapter implemented; real credentials and measured round trip required |
| Farming/weather | Open-Meteo and OGD/AGMARKNET adapters with provenance | Adapters implemented; verify real results, market/date/entity selection |
| Government schemes | Scheme intent/engine foundation | Not yet a versioned, authoritative, effective-date-aware eligibility catalogue |
| Document processing | Sarvam Document AI job adapter | Adapter implemented; consented upload, extraction review and private persistence remain |
| Household memory | Repository interfaces exist; migration added in this change | Schema foundation only; repository integration, auth/RLS tests and consent UI/API enforcement remain |
| Follow-up tasks | Migration and callback eligibility policy added in this change | Policy/schema only; no durable dispatcher or real scheduled callback claim |
| Outbound telephony | Exotel call/AgentStream adapters and security contracts | Real public WSS call and complete call lifecycle must be proven |
| Volunteer panel | Escalation UI/policy | Durable assignment, notes, status and resolution flow remain |
| WhatsApp | No verified end-to-end adapter | Not implemented; do not claim support |
| Evaluation | Synthetic intent benchmark and CI | Add live voice/data measurements and full vertical-slice evidence |

## Changes added in this alignment pass

- supabase/migrations/202610100001_household_memory_and_followups.sql
  - consent defaults to false
  - separate memory and outbound-call consent timestamps
  - minimal household memory, pending-task and volunteer-case records
  - task idempotency key, attempt count, status and due-time index
  - Row Level Security enabled; direct browser-role table access revoked
  - trusted backend/service-role access only
- backend/app/callback_policy.py
  - fail-closed checks for missing/revoked consent, future schedule, non-dispatchable task, retry limit, quiet hours and invalid timezone
  - pure policy only; it does not call Exotel or replace atomic task claiming
- backend/tests/test_callback_policy.py
  - regression tests for the safety decisions above

## Required implementation sequence

### Gate 1 — keep the current prototype truthful
1. Keep demo mode on by default.
2. Verify one real factual tool and its provenance.
3. Verify browser STT → orchestrator → grounded response → TTS with real credentials.
4. Do not call telephony live until a real Exotel call completes against a public WSS endpoint.

### Gate 2 — persistent memory and tasks
1. Review the SQL migration against the actual Supabase project before applying it.
2. Integrate repositories using the backend-only service role; never expose the service key to a browser.
3. Enforce memory consent at every read/write boundary; provide withdrawal and deletion behavior.
4. Enforce outbound consent at task creation and again immediately before every dispatch.
5. Implement atomic task claiming, unique provider idempotency, retries with backoff, call-status webhooks, quiet hours, local timezone, opt-out and a dead-letter state.
6. Add integration tests for cross-household isolation and revoked consent.

### Gate 3 — specialist workflows
1. Version an official scheme catalogue with source URL, effective date and deterministic eligibility rules.
2. Verify mandi commodity, state, district, market, unit and observation date before answering.
3. For documents, persist only minimal metadata initially; expose extracted-field confidence and source page and require human/user confirmation before consequential actions.
4. Build volunteer case assignment, status, notes and resolution backed by durable storage.

### Gate 4 — submission evidence
Capture the exact commit, CI result, configured capabilities, provider provenance, latency/accuracy metrics and a fallback demo run. Keep synthetic demo data labelled. The judge narrative must match what the submitted build actually demonstrates.

## Safety invariants

- Consent is opt-in, not default-on.
- A scheduled task is not proof that a call is authorized.
- Check current consent and opt-out state immediately before each outbound call.
- LLM output is not the source of truth for current prices, weather, scheme eligibility or application status.
- OCR output is untrusted until validated.
- Do not store sensitive transcripts/documents without a defined need, explicit notice/consent, access controls and retention policy.
- Never claim WhatsApp, live telephony, persistent memory or government submission is working without end-to-end evidence.

# Release-gate work remaining

This checklist distinguishes repository-verifiable work from gates that require live
provider credentials, account-owner decisions, or real calls. Never close an issue
solely because a mock or local test passes.

## Work that can be verified in CI

- [ ] Reconcile the existing feature branch with current `main`; resolve conflicts intentionally.
- [ ] Run backend tests, dependency audit, frontend lint, TypeScript, and production build on the final candidate.
- [ ] Keep deterministic intent/entity tests and adversarial tool-policy tests in CI.
- [ ] Expand the synthetic text regression set and report intent/entity metrics separately by language style.
- [ ] Add provider-independent tests for webhook replay handling, signature failures, consent denial, and partial provider failure.
- [ ] Ensure every demo response visibly identifies simulated values and every live fact has source and retrieval time.
- [ ] Verify API authorization, CORS, rate-limit behavior, redacted logs, and readiness capability reporting.

## External gates (cannot be truthfully completed with mocks)

### Supabase (#27, #2, #13, #11)
- [ ] Restore project `ibvgxgvcqcfnoyrlwywa` or provision an authorized replacement.
- [ ] Apply migrations only after reviewing the live schema and project target.
- [ ] Run Supabase security/performance advisors and inspect RLS policies.
- [ ] Test two authenticated households against each other; prove cross-household reads/writes fail.
- [ ] Configure least-privilege server credentials; never expose service-role credentials to the browser.
- [ ] Verify durable webhook idempotency under concurrent duplicate delivery.

The project was reported inactive because the organization had reached its active-project
limit. Do not pause/delete another project without its owner's explicit authorization.

### Real voice and language (#16, #22)
- [ ] Run consented browser STT/TTS tests with actual provider credentials.
- [ ] Capture transcript/audio/turn latency, provider version, errors, and test environment.
- [ ] Run real Exotel WSS calls, including interruptions/barge-in and reconnect/failure paths.
- [ ] Measure WER/CER on a reviewed, synthetic or consented audio set; do not infer WER from text tests.
- [ ] Expand the text dataset to 100–200 reviewed utterances and add audio fixtures before claiming dialect performance.

### Human support, reminders, documents, schemes (#20, #21, #19, #17)
- [ ] Persist volunteer cases, assignments, authorization, status changes, and audit trail.
- [ ] Schedule reminders durably with consent, quiet hours, retries, cancellation, and outbound-call audit.
- [ ] Store documents privately; validate type/size, enforce consent, score extraction confidence, and require review for low-confidence fields.
- [ ] Add versioned, source-backed scheme records with effective dates and deterministic eligibility rules.

## Closure rule

Close an issue only when its acceptance criteria are implemented, tests pass, required live
integration evidence is attached, and the README/demo claims match the tested behavior.

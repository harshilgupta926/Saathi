-- Saathi household, task, volunteer and call persistence on shared Nihdhoom.
-- All objects are namespaced. Only the trusted backend service_role may access them.
-- Memory records are blocked at the database layer unless current memory consent exists.

CREATE TABLE IF NOT EXISTS public.saathi_households (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  phone_number text UNIQUE NULL CHECK (phone_number IS NULL OR length(phone_number) BETWEEN 7 AND 20),
  preferred_language text NOT NULL DEFAULT 'hi' CHECK (length(preferred_language) BETWEEN 2 AND 20),
  dialect_context jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(dialect_context) = 'object'),
  memory_consent boolean NOT NULL DEFAULT false,
  memory_consent_at timestamptz NULL,
  outbound_call_consent boolean NOT NULL DEFAULT false,
  outbound_call_consent_at timestamptz NULL,
  consent_revoked_at timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT saathi_household_memory_consent_timestamp
    CHECK (memory_consent = false OR memory_consent_at IS NOT NULL),
  CONSTRAINT saathi_household_call_consent_timestamp
    CHECK (outbound_call_consent = false OR outbound_call_consent_at IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS public.saathi_household_memories (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  household_id uuid NOT NULL REFERENCES public.saathi_households(id) ON DELETE CASCADE,
  memory_type text NOT NULL CHECK (length(memory_type) BETWEEN 1 AND 80),
  key_name text NOT NULL CHECK (length(key_name) BETWEEN 1 AND 120),
  value_text text NOT NULL CHECK (length(value_text) <= 2000),
  source text NOT NULL DEFAULT 'user_confirmed'
    CHECK (source IN ('user_confirmed', 'derived', 'official')),
  updated_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NULL,
  UNIQUE (household_id, memory_type, key_name)
);
CREATE INDEX IF NOT EXISTS saathi_household_memories_expiry_idx
  ON public.saathi_household_memories (expires_at) WHERE expires_at IS NOT NULL;

CREATE OR REPLACE FUNCTION public.saathi_enforce_memory_consent()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog, public
AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM public.saathi_households h
    WHERE h.id = NEW.household_id
      AND h.memory_consent IS TRUE
      AND h.memory_consent_at IS NOT NULL
      AND (h.consent_revoked_at IS NULL OR h.consent_revoked_at < h.memory_consent_at)
  ) THEN
    RAISE EXCEPTION 'household_memory_consent_required' USING ERRCODE = '42501';
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.saathi_enforce_memory_consent() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.saathi_enforce_memory_consent() TO service_role;

DROP TRIGGER IF EXISTS saathi_household_memory_consent_guard ON public.saathi_household_memories;
CREATE TRIGGER saathi_household_memory_consent_guard
  BEFORE INSERT OR UPDATE ON public.saathi_household_memories
  FOR EACH ROW EXECUTE FUNCTION public.saathi_enforce_memory_consent();

CREATE TABLE IF NOT EXISTS public.saathi_pending_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  household_id uuid NOT NULL REFERENCES public.saathi_households(id) ON DELETE CASCADE,
  title text NOT NULL CHECK (length(title) BETWEEN 1 AND 300),
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'scheduled', 'in_progress', 'completed', 'cancelled', 'escalated', 'failed')),
  missing_requirements text[] NOT NULL DEFAULT '{}',
  scheduled_callback timestamptz NULL,
  timezone_name text NOT NULL DEFAULT 'Asia/Kolkata',
  idempotency_key text NOT NULL UNIQUE CHECK (length(idempotency_key) BETWEEN 1 AND 200),
  callback_attempts integer NOT NULL DEFAULT 0 CHECK (callback_attempts >= 0),
  last_attempt_at timestamptz NULL,
  completed_at timestamptz NULL,
  cancelled_at timestamptz NULL,
  last_error_code text NULL CHECK (last_error_code IS NULL OR length(last_error_code) <= 120),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS saathi_pending_tasks_due_idx
  ON public.saathi_pending_tasks (scheduled_callback)
  WHERE status IN ('pending', 'scheduled');
CREATE INDEX IF NOT EXISTS saathi_pending_tasks_household_status_idx
  ON public.saathi_pending_tasks (household_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS public.saathi_volunteer_cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  household_id uuid NULL REFERENCES public.saathi_households(id) ON DELETE SET NULL,
  task_id uuid NULL REFERENCES public.saathi_pending_tasks(id) ON DELETE SET NULL,
  status text NOT NULL DEFAULT 'open'
    CHECK (status IN ('open', 'assigned', 'in_progress', 'resolved', 'closed')),
  priority text NOT NULL DEFAULT 'normal'
    CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
  summary text NOT NULL CHECK (length(summary) BETWEEN 1 AND 2000),
  assigned_to text NULL CHECK (assigned_to IS NULL OR length(assigned_to) <= 200),
  resolution_note text NULL CHECK (resolution_note IS NULL OR length(resolution_note) <= 2000),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  resolved_at timestamptz NULL
);
CREATE INDEX IF NOT EXISTS saathi_volunteer_cases_open_idx
  ON public.saathi_volunteer_cases (priority, created_at)
  WHERE status IN ('open', 'assigned', 'in_progress');

CREATE TABLE IF NOT EXISTS public.saathi_calls (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  call_id text NOT NULL UNIQUE CHECK (length(call_id) BETWEEN 1 AND 200),
  household_id uuid NULL REFERENCES public.saathi_households(id) ON DELETE SET NULL,
  phone_number text NOT NULL CHECK (length(phone_number) BETWEEN 7 AND 20),
  direction text NOT NULL CHECK (direction IN ('inbound', 'outbound')),
  status text NOT NULL DEFAULT 'received'
    CHECK (status IN ('received', 'connecting', 'in_progress', 'completed', 'failed', 'escalated')),
  provider text NOT NULL CHECK (length(provider) BETWEEN 1 AND 80),
  provider_call_id text NULL UNIQUE CHECK (provider_call_id IS NULL OR length(provider_call_id) <= 200),
  language text NOT NULL DEFAULT 'hi' CHECK (length(language) BETWEEN 2 AND 20),
  started_at timestamptz NOT NULL DEFAULT now(),
  ended_at timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (ended_at IS NULL OR ended_at >= started_at)
);
CREATE INDEX IF NOT EXISTS saathi_calls_household_started_idx
  ON public.saathi_calls (household_id, started_at DESC) WHERE household_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.saathi_call_events (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  call_id uuid NULL REFERENCES public.saathi_calls(id) ON DELETE SET NULL,
  provider_event_id text NOT NULL UNIQUE CHECK (length(provider_event_id) BETWEEN 1 AND 200),
  event_type text NOT NULL CHECK (length(event_type) BETWEEN 1 AND 120),
  processing_status text NOT NULL DEFAULT 'received'
    CHECK (processing_status IN ('received', 'processing', 'processed', 'failed')),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata) = 'object'),
  received_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz NULL
);
CREATE INDEX IF NOT EXISTS saathi_call_events_status_idx
  ON public.saathi_call_events (processing_status, received_at);

DO $$
DECLARE
  table_name text;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'saathi_households',
    'saathi_household_memories',
    'saathi_pending_tasks',
    'saathi_volunteer_cases',
    'saathi_calls',
    'saathi_call_events'
  ] LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated', table_name);
    EXECUTE format('GRANT ALL ON TABLE public.%I TO service_role', table_name);
  END LOOP;
END;
$$;
GRANT USAGE, SELECT ON SEQUENCE public.saathi_call_events_id_seq TO service_role;

CREATE POLICY saathi_households_deny_client_access
  ON public.saathi_households FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
CREATE POLICY saathi_household_memories_deny_client_access
  ON public.saathi_household_memories FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
CREATE POLICY saathi_pending_tasks_deny_client_access
  ON public.saathi_pending_tasks FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
CREATE POLICY saathi_volunteer_cases_deny_client_access
  ON public.saathi_volunteer_cases FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
CREATE POLICY saathi_calls_deny_client_access
  ON public.saathi_calls FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
CREATE POLICY saathi_call_events_deny_client_access
  ON public.saathi_call_events FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);

COMMENT ON TABLE public.saathi_households IS
  'Saathi household record; phone data is sensitive and accessible only to the trusted backend.';
COMMENT ON TABLE public.saathi_household_memories IS
  'Minimal consent-gated household facts; raw transcripts and sensitive document contents are prohibited.';
COMMENT ON TABLE public.saathi_pending_tasks IS
  'Saathi follow-up queue. A dispatcher must re-check outbound consent, opt-out, quiet hours and retry limits before every call.';
COMMENT ON TABLE public.saathi_volunteer_cases IS
  'Human support cases with minimal summaries; do not store raw transcripts by default.';
COMMENT ON TABLE public.saathi_calls IS
  'Call metadata including PII; service-role only and subject to retention/deletion policy.';
COMMENT ON TABLE public.saathi_call_events IS
  'Idempotent provider event ledger; metadata must be redacted and must not include raw payloads or secrets.';

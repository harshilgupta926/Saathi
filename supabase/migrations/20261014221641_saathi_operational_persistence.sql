-- Saathi operational persistence on the shared Nihdhoom Supabase project.
-- These names are intentionally namespaced to avoid collisions with Nihdhoom.
-- Browser roles have no access; the trusted backend uses service_role only.

CREATE TABLE IF NOT EXISTS public.saathi_conversations (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  household_id uuid NULL,
  agent_used text NOT NULL CHECK (length(agent_used) <= 100),
  tools_called jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(tools_called) = 'array'),
  confidence_score numeric NULL CHECK (confidence_score IS NULL OR confidence_score BETWEEN 0 AND 1),
  language_code text NOT NULL DEFAULT 'hi' CHECK (length(language_code) BETWEEN 1 AND 20),
  correlation_id text NULL CHECK (correlation_id IS NULL OR length(correlation_id) <= 128),
  response_class text NOT NULL CHECK (length(response_class) BETWEEN 1 AND 40),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS saathi_conversations_created_at_idx
  ON public.saathi_conversations (created_at DESC);
CREATE INDEX IF NOT EXISTS saathi_conversations_household_id_idx
  ON public.saathi_conversations (household_id) WHERE household_id IS NOT NULL;

ALTER TABLE public.saathi_conversations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.saathi_conversations FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.saathi_conversations TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.saathi_conversations_id_seq TO service_role;

CREATE TABLE IF NOT EXISTS public.saathi_telephony_webhook_events (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_id text NOT NULL UNIQUE CHECK (length(event_id) BETWEEN 1 AND 200),
  event_type text NULL CHECK (event_type IS NULL OR length(event_type) <= 120),
  processing_status text NOT NULL DEFAULT 'received'
    CHECK (processing_status IN ('received', 'processing', 'processed', 'failed')),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS saathi_telephony_webhook_events_created_at_idx
  ON public.saathi_telephony_webhook_events (created_at DESC);

ALTER TABLE public.saathi_telephony_webhook_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.saathi_telephony_webhook_events FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE public.saathi_telephony_webhook_events TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.saathi_telephony_webhook_events_id_seq TO service_role;

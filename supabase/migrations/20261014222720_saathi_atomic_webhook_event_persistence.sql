-- Atomically persist the webhook idempotency claim and its call-event ledger row.
CREATE OR REPLACE FUNCTION public.saathi_record_webhook_event(
  p_event_id text,
  p_event_type text DEFAULT NULL
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog, public
AS $$
DECLARE
  is_duplicate boolean;
  normalized_event_type text;
BEGIN
  IF p_event_id IS NULL OR length(btrim(p_event_id)) < 1 OR length(btrim(p_event_id)) > 200 THEN
    RAISE EXCEPTION 'valid_provider_event_id_required' USING ERRCODE = '22023';
  END IF;

  normalized_event_type := left(coalesce(nullif(btrim(p_event_type), ''), 'unknown'), 120);

  INSERT INTO public.saathi_telephony_webhook_events(event_id, event_type, processing_status)
  VALUES (btrim(p_event_id), normalized_event_type, 'received')
  ON CONFLICT (event_id) DO NOTHING;

  is_duplicate := NOT FOUND;

  INSERT INTO public.saathi_call_events(provider_event_id, event_type, processing_status, metadata)
  VALUES (btrim(p_event_id), normalized_event_type, 'received', '{}'::jsonb)
  ON CONFLICT (provider_event_id) DO NOTHING;

  RETURN is_duplicate;
END;
$$;
REVOKE ALL ON FUNCTION public.saathi_record_webhook_event(text, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.saathi_record_webhook_event(text, text) TO service_role;

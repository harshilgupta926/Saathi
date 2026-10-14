-- Serialize memory writes against consent revocation to prevent a race leaving stale memory.
CREATE OR REPLACE FUNCTION public.saathi_enforce_memory_consent()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog, public
AS $$
DECLARE
  household_row public.saathi_households%ROWTYPE;
BEGIN
  SELECT * INTO household_row
  FROM public.saathi_households
  WHERE id = NEW.household_id
  FOR UPDATE;

  IF NOT FOUND
     OR household_row.memory_consent IS NOT TRUE
     OR household_row.memory_consent_at IS NULL
     OR (
       household_row.memory_consent_revoked_at IS NOT NULL
       AND household_row.memory_consent_revoked_at >= household_row.memory_consent_at
     )
  THEN
    RAISE EXCEPTION 'household_memory_consent_required' USING ERRCODE = '42501';
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.saathi_enforce_memory_consent() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.saathi_enforce_memory_consent() TO service_role;

-- Separate consent revocation timestamps by purpose and erase memory on revocation.
ALTER TABLE public.saathi_households
  ADD COLUMN IF NOT EXISTS memory_consent_revoked_at timestamptz NULL,
  ADD COLUMN IF NOT EXISTS outbound_call_consent_revoked_at timestamptz NULL;

COMMENT ON COLUMN public.saathi_households.consent_revoked_at IS
  'Legacy aggregate timestamp; new logic must use the purpose-specific revocation timestamps.';

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
      AND (h.memory_consent_revoked_at IS NULL OR h.memory_consent_revoked_at < h.memory_consent_at)
  ) THEN
    RAISE EXCEPTION 'household_memory_consent_required' USING ERRCODE = '42501';
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.saathi_enforce_memory_consent() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.saathi_enforce_memory_consent() TO service_role;

CREATE OR REPLACE FUNCTION public.saathi_purge_memory_on_revocation()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog, public
AS $$
BEGIN
  IF OLD.memory_consent IS TRUE AND (
    NEW.memory_consent IS FALSE
    OR (
      NEW.memory_consent_revoked_at IS NOT NULL
      AND NEW.memory_consent_at IS NOT NULL
      AND NEW.memory_consent_revoked_at >= NEW.memory_consent_at
    )
  ) THEN
    DELETE FROM public.saathi_household_memories WHERE household_id = NEW.id;
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.saathi_purge_memory_on_revocation() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.saathi_purge_memory_on_revocation() TO service_role;

DROP TRIGGER IF EXISTS saathi_household_memory_revocation_purge ON public.saathi_households;
CREATE TRIGGER saathi_household_memory_revocation_purge
  AFTER UPDATE OF memory_consent, memory_consent_revoked_at ON public.saathi_households
  FOR EACH ROW EXECUTE FUNCTION public.saathi_purge_memory_on_revocation();

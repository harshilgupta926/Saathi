-- Defense in depth for Saathi tables on the shared Nihdhoom project.
-- Browser roles have neither table access nor sequence access.
CREATE POLICY saathi_conversations_deny_client_access
  ON public.saathi_conversations FOR ALL TO anon, authenticated
  USING (false) WITH CHECK (false);

CREATE POLICY saathi_telephony_webhook_events_deny_client_access
  ON public.saathi_telephony_webhook_events FOR ALL TO anon, authenticated
  USING (false) WITH CHECK (false);

REVOKE ALL ON SEQUENCE public.saathi_conversations_id_seq FROM PUBLIC, anon, authenticated;
REVOKE ALL ON SEQUENCE public.saathi_telephony_webhook_events_id_seq FROM PUBLIC, anon, authenticated;
REVOKE ALL ON SEQUENCE public.saathi_call_events_id_seq FROM PUBLIC, anon, authenticated;

GRANT USAGE, SELECT ON SEQUENCE public.saathi_conversations_id_seq TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.saathi_telephony_webhook_events_id_seq TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.saathi_call_events_id_seq TO service_role;

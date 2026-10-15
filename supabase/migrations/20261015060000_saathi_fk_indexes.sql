-- Saathi-only foreign-key indexes flagged by the Nihdhoom performance advisor.
-- Reviewed as forward-only, non-destructive DDL. Do not apply until migration
-- history is reconciled and this migration is approved for the target environment.
CREATE INDEX IF NOT EXISTS saathi_call_events_call_id_idx
  ON public.saathi_call_events (call_id);
CREATE INDEX IF NOT EXISTS saathi_volunteer_cases_household_id_idx
  ON public.saathi_volunteer_cases (household_id);
CREATE INDEX IF NOT EXISTS saathi_volunteer_cases_task_id_idx
  ON public.saathi_volunteer_cases (task_id);

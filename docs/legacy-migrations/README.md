# Quarantined legacy migrations

These two SQL files were present in the historical active migration directory but create unprefixed objects in the shared `public` schema. The inspected Nihdhoom project records six later Saathi-prefixed migrations and has no matching unprefixed tables or legacy migration versions in its migration history.

They are preserved here for auditability, with the `.sql.disabled` suffix and outside `supabase/migrations/` so Supabase CLI migration discovery will not apply them. Do not restore or execute them. If another environment depends on these legacy versions, reconcile that environment explicitly before merging this change; never create or modify unprefixed shared tables as a workaround.

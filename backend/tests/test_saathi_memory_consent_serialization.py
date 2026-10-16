from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "supabase" / "migrations"
LOCKING = MIGRATIONS / "20261014222432_saathi_memory_consent_locking.sql"
GUARD = MIGRATIONS / "20261014222114_saathi_household_task_call_foundation.sql"


def test_active_memory_consent_guard_locks_household_before_authorizing_write():
    sql = LOCKING.read_text(encoding="utf-8")
    assert "CREATE OR REPLACE FUNCTION public.saathi_enforce_memory_consent()" in sql
    assert "FOR UPDATE;" in sql
    assert "household_row.memory_consent IS NOT TRUE" in sql
    assert "household_row.memory_consent_at IS NULL" in sql
    assert "household_row.memory_consent_revoked_at >= household_row.memory_consent_at" in sql
    assert "household_memory_consent_required" in sql
    assert "GRANT EXECUTE ON FUNCTION public.saathi_enforce_memory_consent() TO service_role" in sql


def test_memory_consent_guard_is_attached_to_the_memory_table():
    sql = GUARD.read_text(encoding="utf-8")
    assert "CREATE TRIGGER saathi_household_memory_consent_guard" in sql
    assert "BEFORE INSERT OR UPDATE ON public.saathi_household_memories" in sql
    assert "EXECUTE FUNCTION public.saathi_enforce_memory_consent()" in sql
    assert LOCKING.name in {path.name for path in MIGRATIONS.glob("*.sql")}
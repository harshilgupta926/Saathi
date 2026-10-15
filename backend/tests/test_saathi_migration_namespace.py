from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "supabase" / "migrations"
UNPREFIXED_SHARED_TABLES = {
    "households",
    "household_memories",
    "pending_tasks",
    "volunteer_cases",
    "conversations",
    "telephony_webhook_events",
}


def _sql_without_comments(path: Path) -> str:
    sql = path.read_text(encoding="utf-8")
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.S)
    return re.sub(r"--[^\n]*", "", sql)


def test_active_migrations_create_only_saathi_prefixed_tables():
    migration_files = sorted(MIGRATIONS.glob("*.sql"))
    assert migration_files, "expected active Saathi migration files"
    created_tables = []
    for path in migration_files:
        sql = _sql_without_comments(path)
        created_tables.extend(
            match.group(1).lower()
            for match in re.finditer(
                r"\bcreate\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?([a-z_][a-z0-9_]*)",
                sql,
                flags=re.I,
            )
        )
    assert created_tables, "expected table declarations in active migrations"
    assert all(name.startswith("saathi_") for name in created_tables), created_tables


def test_active_migrations_do_not_reference_legacy_unprefixed_shared_tables():
    pattern = re.compile(
        r"\b(?:create\s+table(?:\s+if\s+not\s+exists)?|alter\s+table|references|on)\s+"
        r"(?:public\.)?(" + "|".join(sorted(UNPREFIXED_SHARED_TABLES)) + r")\b",
        flags=re.I,
    )
    violations = []
    for path in sorted(MIGRATIONS.glob("*.sql")):
        for match in pattern.finditer(_sql_without_comments(path)):
            violations.append(f"{path.name}: {match.group(1)}")
    assert not violations, violations


def test_legacy_migrations_are_quarantined_outside_active_discovery():
    assert not (MIGRATIONS / "202610100001_household_memory_and_followups.sql").exists()
    assert not (MIGRATIONS / "202610100002_conversation_audit_and_webhook_idempotency.sql").exists()
    legacy = ROOT / "docs" / "legacy-migrations"
    assert (legacy / "202610100001_household_memory_and_followups.sql.disabled").is_file()
    assert (legacy / "202610100002_conversation_audit_and_webhook_idempotency.sql.disabled").is_file()

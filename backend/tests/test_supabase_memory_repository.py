import asyncio
from datetime import datetime, timezone

import pytest

from app.supabase_repositories import SupabaseMemoryRepository, SupabaseRepositoryError


HOUSEHOLD_ID = "22222222-2222-4222-8222-222222222222"
MEMORY_ID = "33333333-3333-4333-8333-333333333333"


def test_save_marks_memory_user_confirmed_and_returns_only_public_fields(monkeypatch):
    repository = SupabaseMemoryRepository()
    captured = {}

    async def request(method, path, payload=None):
        captured.update(method=method, path=path, payload=payload)
        return [{
            "id": MEMORY_ID,
            "memory_type": "preference",
            "key_name": "crop",
            "value_text": "wheat",
            "source": "user_confirmed",
            "updated_at": "2026-10-15T10:00:00+00:00",
            "expires_at": None,
            "household_id": HOUSEHOLD_ID,
        }]

    monkeypatch.setattr(repository, "_request", request)
    result = asyncio.run(repository.save(
        household_id=HOUSEHOLD_ID,
        memory_type="preference",
        key_name="crop",
        value_text="wheat",
    ))
    assert captured["method"] == "POST"
    assert captured["payload"]["source"] == "user_confirmed"
    assert captured["payload"]["household_id"] == HOUSEHOLD_ID
    assert "household_id" not in result
    assert result["memory_id"] == MEMORY_ID


def test_duplicate_memory_update_is_scoped_to_household_and_key(monkeypatch):
    repository = SupabaseMemoryRepository()
    calls = []

    async def request(method, path, payload=None):
        calls.append((method, path, payload))
        if method == "POST":
            raise SupabaseRepositoryError("supabase_persistence_http_409")
        return [{
            "id": MEMORY_ID,
            "memory_type": "preference",
            "key_name": "crop type",
            "value_text": "wheat",
            "source": "user_confirmed",
            "updated_at": "2026-10-15T10:00:00+00:00",
            "expires_at": None,
        }]

    monkeypatch.setattr(repository, "_request", request)
    result = asyncio.run(repository.save(
        household_id=HOUSEHOLD_ID,
        memory_type="preference",
        key_name="crop type",
        value_text="wheat",
    ))
    assert calls[1][0] == "PATCH"
    assert f"household_id=eq.{HOUSEHOLD_ID}" in calls[1][1]
    assert "memory_type=eq.preference" in calls[1][1]
    assert "key_name=eq.crop%20type" in calls[1][1]
    assert result["key_name"] == "crop type"


def test_database_consent_guard_failure_is_not_retried(monkeypatch):
    repository = SupabaseMemoryRepository()

    async def request(method, path, payload=None):
        raise SupabaseRepositoryError("supabase_persistence_http_403")

    monkeypatch.setattr(repository, "_request", request)
    with pytest.raises(SupabaseRepositoryError, match="household_memory_consent_required"):
        asyncio.run(repository.save(
            household_id=HOUSEHOLD_ID,
            memory_type="preference",
            key_name="crop",
            value_text="wheat",
        ))


def test_delete_filters_by_both_memory_and_household(monkeypatch):
    repository = SupabaseMemoryRepository()
    captured = {}

    async def request(method, path, payload=None):
        captured.update(method=method, path=path)
        return [{"id": MEMORY_ID}]

    monkeypatch.setattr(repository, "_request", request)
    assert asyncio.run(repository.delete(household_id=HOUSEHOLD_ID, memory_id=MEMORY_ID)) is True
    assert captured["method"] == "DELETE"
    assert f"id=eq.{MEMORY_ID}" in captured["path"]
    assert f"household_id=eq.{HOUSEHOLD_ID}" in captured["path"]


def test_list_hides_expired_memory(monkeypatch):
    repository = SupabaseMemoryRepository()

    async def request(method, path, payload=None):
        return [
            {"id": MEMORY_ID, "memory_type": "preference", "key_name": "old", "value_text": "expired", "source": "user_confirmed", "updated_at": "2026-10-01T00:00:00+00:00", "expires_at": "2026-10-02T00:00:00+00:00"},
            {"id": "44444444-4444-4444-8444-444444444444", "memory_type": "preference", "key_name": "current", "value_text": "wheat", "source": "user_confirmed", "updated_at": datetime.now(timezone.utc).isoformat(), "expires_at": None},
        ]

    monkeypatch.setattr(repository, "_request", request)
    memories = asyncio.run(repository.list_for_household(household_id=HOUSEHOLD_ID))
    assert [memory["key_name"] for memory in memories] == ["current"]
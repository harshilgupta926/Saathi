from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.domain import Consent, ConsentType
from app.main import app
from app.supabase_repositories import SupabaseRepositoryError


HOUSEHOLD_ID = "22222222-2222-4222-8222-222222222222"
IDENTITY_ID = "11111111-1111-4111-8111-111111111111"
MEMORY_ID = "33333333-3333-4333-8333-333333333333"


def configure_production(monkeypatch):
    monkeypatch.setenv("SAATHI_HOUSEHOLD_FEATURES_ENABLED", "true")
    monkeypatch.setattr(
        "app.main.settings",
        SimpleNamespace(app_env="production", demo_mode=False, api_auth_token="server-token"),
    )


def headers():
    return {
        "X-Saathi-API-Key": "server-token",
        "X-Saathi-Verified-Identity": IDENTITY_ID,
        "X-Saathi-Verified-Household": HOUSEHOLD_ID,
    }


def test_memory_list_requires_verified_household(monkeypatch):
    configure_production(monkeypatch)
    response = TestClient(app).get("/api/v1/household/memories", headers={"X-Saathi-API-Key": "server-token"})
    assert response.status_code == 401


def test_memory_list_returns_empty_when_consent_is_off(monkeypatch):
    configure_production(monkeypatch)

    async def get(self, *, household_id, consent_type):
        assert household_id == HOUSEHOLD_ID
        assert consent_type == ConsentType.MEMORY
        return None

    async def list_for_household(self, *, household_id):
        raise AssertionError("memory rows must not be queried without consent")

    monkeypatch.setattr("app.main.SupabaseConsentRepository.get", get)
    monkeypatch.setattr("app.main.SupabaseMemoryRepository.list_for_household", list_for_household)
    response = TestClient(app).get("/api/v1/household/memories", headers=headers())
    assert response.status_code == 200
    assert response.json() == {"consent_granted": False, "memories": []}


def test_memory_write_requires_explicit_persisted_consent(monkeypatch):
    configure_production(monkeypatch)

    async def get(self, *, household_id, consent_type):
        return None

    async def save(self, **kwargs):
        raise AssertionError("memory write must not run without consent")

    monkeypatch.setattr("app.main.SupabaseConsentRepository.get", get)
    monkeypatch.setattr("app.main.SupabaseMemoryRepository.save", save)
    response = TestClient(app).post(
        "/api/v1/household/memories",
        headers=headers(),
        json={"memory_type": "preference", "key_name": "crop", "value_text": "wheat"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "memory_consent_required"


def test_memory_write_uses_verified_household_and_user_confirmed_source(monkeypatch):
    configure_production(monkeypatch)
    captured = {}

    async def get(self, *, household_id, consent_type):
        return Consent(household_id=household_id, consent_type=consent_type, granted=True, recorded_at=datetime.now(timezone.utc))

    async def save(self, **kwargs):
        captured.update(kwargs)
        return {
            "memory_id": MEMORY_ID,
            "memory_type": kwargs["memory_type"],
            "key_name": kwargs["key_name"],
            "value_text": kwargs["value_text"],
            "source": "user_confirmed",
            "updated_at": "2026-10-15T10:00:00+00:00",
            "expires_at": None,
        }

    monkeypatch.setattr("app.main.SupabaseConsentRepository.get", get)
    monkeypatch.setattr("app.main.SupabaseMemoryRepository.save", save)
    response = TestClient(app).post(
        "/api/v1/household/memories",
        headers=headers(),
        json={"memory_type": " preference ", "key_name": " crop ", "value_text": " wheat "},
    )
    assert response.status_code == 200
    assert response.json()["source"] == "user_confirmed"
    assert captured == {
        "household_id": HOUSEHOLD_ID,
        "memory_type": "preference",
        "key_name": "crop",
        "value_text": "wheat",
    }


def test_memory_database_guard_race_fails_closed_as_forbidden(monkeypatch):
    configure_production(monkeypatch)

    async def get(self, *, household_id, consent_type):
        return Consent(household_id=household_id, consent_type=consent_type, granted=True, recorded_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))

    async def save(self, **kwargs):
        raise SupabaseRepositoryError("household_memory_consent_required")

    monkeypatch.setattr("app.main.SupabaseConsentRepository.get", get)
    monkeypatch.setattr("app.main.SupabaseMemoryRepository.save", save)
    response = TestClient(app).post(
        "/api/v1/household/memories",
        headers=headers(),
        json={"memory_type": "preference", "key_name": "crop", "value_text": "wheat"},
    )
    assert response.status_code == 403


def test_memory_delete_is_household_scoped(monkeypatch):
    configure_production(monkeypatch)
    captured = {}

    async def delete(self, *, household_id, memory_id):
        captured.update(household_id=household_id, memory_id=memory_id)
        return True

    monkeypatch.setattr("app.main.SupabaseMemoryRepository.delete", delete)
    response = TestClient(app).post(
        "/api/v1/household/memories/delete",
        headers=headers(),
        json={"memory_id": MEMORY_ID},
    )
    assert response.status_code == 200
    assert response.json() == {"memory_id": MEMORY_ID, "deleted": True}
    assert captured == {"household_id": HOUSEHOLD_ID, "memory_id": MEMORY_ID}


def test_memory_write_rejects_client_supplied_household_id(monkeypatch):
    configure_production(monkeypatch)
    response = TestClient(app).post(
        "/api/v1/household/memories",
        headers=headers(),
        json={"memory_type": "preference", "key_name": "crop", "value_text": "wheat", "household_id": "44444444-4444-4444-8444-444444444444"},
    )
    assert response.status_code == 422
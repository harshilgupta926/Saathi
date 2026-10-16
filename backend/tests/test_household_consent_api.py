from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.domain import Consent, ConsentType
from app.main import app


def configure_production(monkeypatch):
    monkeypatch.setenv("SAATHI_HOUSEHOLD_FEATURES_ENABLED", "true")
    monkeypatch.setattr(
        "app.main.settings",
        SimpleNamespace(app_env="production", demo_mode=False, api_auth_token="server-token"),
    )


def headers():
    return {
        "X-Saathi-API-Key": "server-token",
        "X-Saathi-Verified-Identity": "11111111-1111-4111-8111-111111111111",
        "X-Saathi-Verified-Household": "22222222-2222-4222-8222-222222222222",
    }


def test_consent_status_requires_verified_household_context(monkeypatch):
    configure_production(monkeypatch)
    response = TestClient(app).get("/api/v1/household/consent", headers={"X-Saathi-API-Key": "server-token"})
    assert response.status_code == 401
    assert response.json()["detail"] == "verified_phone_identity_required"


def test_consent_status_returns_purpose_specific_grants(monkeypatch):
    configure_production(monkeypatch)
    recorded = datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc)

    async def get(self, *, household_id, consent_type):
        assert household_id == "22222222-2222-4222-8222-222222222222"
        if consent_type == ConsentType.MEMORY:
            return Consent(household_id=household_id, consent_type=consent_type, granted=True, recorded_at=recorded)
        return None

    monkeypatch.setattr("app.main.SupabaseConsentRepository.get", get)
    response = TestClient(app).get("/api/v1/household/consent", headers=headers())
    assert response.status_code == 200
    body = response.json()
    assert body["memory"]["granted"] is True
    assert body["memory"]["recorded_at"] == recorded.isoformat()
    assert body["outbound_calls"]["granted"] is False


def test_consent_update_persists_explicit_purpose_and_grant(monkeypatch):
    configure_production(monkeypatch)
    captured = {}

    async def save(self, consent):
        captured["consent"] = consent
        return consent

    monkeypatch.setattr("app.main.SupabaseConsentRepository.save", save)
    response = TestClient(app).post(
        "/api/v1/household/consent",
        headers=headers(),
        json={"purpose": "outbound_calls", "granted": True},
    )
    assert response.status_code == 200
    assert response.json()["purpose"] == "outbound_calls"
    assert response.json()["granted"] is True
    assert captured["consent"].household_id == "22222222-2222-4222-8222-222222222222"
    assert captured["consent"].consent_type == ConsentType.OUTBOUND_CALLS
    assert captured["consent"].granted is True


def test_consent_update_rejects_client_supplied_household_id(monkeypatch):
    configure_production(monkeypatch)
    response = TestClient(app).post(
        "/api/v1/household/consent",
        headers=headers(),
        json={"purpose": "memory", "granted": True, "household_id": "33333333-3333-4333-8333-333333333333"},
    )
    assert response.status_code == 422
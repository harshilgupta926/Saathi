from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.domain import Consent, ConsentType
from app.main import app


def production_call_settings():
    return SimpleNamespace(
        app_env="production",
        demo_mode=False,
        call_api_token="call-token",
        exotel_account_sid="account",
        exotel_api_key="api-key",
        exotel_api_token="api-token",
        exotel_virtual_number="+911234567890",
        exotel_subdomain="api.in.exotel.com",
        exotel_stream_url=None,
        telephony_callback_url="https://saathi.example.com/api/v1/webhooks/telephony",
        telephony_callback_signature_verified=True,
    )


def live_call_payload(household_id="11111111-1111-4111-8111-111111111111"):
    return {
        "to": "+919999999999",
        "callback_url": "https://example.test/callback",
        "consent": True,
        "household_id": household_id,
        "language": "hi",
    }


def test_outbound_call_requires_explicit_consent():
    response = TestClient(app).post(
        "/api/v1/calls",
        json={"to": "+919999999999", "callback_url": "https://example.test/callback", "consent": False},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "explicit_outbound_call_consent_required"


def test_demo_outbound_call_is_unavailable_and_never_calls_provider(monkeypatch):
    async def unexpected_provider_call(self, **kwargs):
        raise AssertionError("demo mode must never call Exotel")

    monkeypatch.setattr("app.main.ExotelTelephonyProvider.place_call", unexpected_provider_call)
    monkeypatch.setattr("app.main.ExotelTelephonyProvider.place_voice_ai_call", unexpected_provider_call)
    client = TestClient(app)

    # Both regular and realtime requests must remain explicitly unavailable.
    for realtime in (False, True):
        response = client.post(
            "/api/v1/calls",
            json={
                "to": "+919999999999",
                "callback_url": "https://example.test/callback",
                "consent": True,
                "realtime_voice_ai": realtime,
            },
        )
        assert response.status_code == 503
        body = response.json()
        assert body["detail"] == "telephony_unavailable_in_demo_mode"
        assert "call_id" not in body
        assert "accepted" not in str(body).casefold()


def test_live_call_fails_closed_without_recorded_outbound_consent(monkeypatch):
    monkeypatch.setattr("app.main.settings", production_call_settings())

    async def no_consent(self, *, household_id, consent_type):
        assert consent_type == ConsentType.OUTBOUND_CALLS
        return None

    async def unexpected_provider_call(self, **kwargs):
        raise AssertionError("provider must not be called without stored consent")

    monkeypatch.setattr("app.main.SupabaseConsentRepository.get", no_consent)
    monkeypatch.setattr("app.main.ExotelTelephonyProvider.place_call", unexpected_provider_call)

    response = TestClient(app).post(
        "/api/v1/calls",
        headers={"Authorization": "Bearer call-token"},
        json=live_call_payload(),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "recorded_outbound_call_consent_required"


def test_live_call_records_before_provider_and_updates_after_acceptance(monkeypatch):
    monkeypatch.setattr("app.main.settings", production_call_settings())
    household_id = "11111111-1111-4111-8111-111111111111"
    internal_call_id = "33333333-3333-4333-8333-333333333333"
    events = []

    async def granted_consent(self, *, household_id, consent_type):
        events.append("consent")
        return Consent(
            household_id=household_id,
            consent_type=ConsentType.OUTBOUND_CALLS,
            granted=True,
            recorded_at=datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc),
        )

    async def create_call(self, *, household_id, phone_number, provider, language):
        events.append("persist_before_provider")
        assert household_id == household_id_arg
        assert provider == "exotel"
        return internal_call_id

    async def mark_accepted(self, *, call_id, provider_call_id):
        events.append("persist_provider_acceptance")
        assert call_id == internal_call_id
        assert provider_call_id == "provider-call-1"

    async def mark_failed(self, *, call_id):
        raise AssertionError("failed state must not be written for an accepted call")

    async def place_call(self, *, to, callback_url):
        events.append("provider")
        assert to == "+919999999999"
        return "provider-call-1"

    household_id_arg = household_id
    monkeypatch.setattr("app.main.SupabaseConsentRepository.get", granted_consent)
    monkeypatch.setattr("app.main.SupabaseCallRepository.create", create_call)
    monkeypatch.setattr("app.main.SupabaseCallRepository.mark_accepted", mark_accepted)
    monkeypatch.setattr("app.main.SupabaseCallRepository.mark_failed", mark_failed)
    monkeypatch.setattr("app.main.ExotelTelephonyProvider.place_call", place_call)

    response = TestClient(app).post(
        "/api/v1/calls",
        headers={"Authorization": "Bearer call-token"},
        json=live_call_payload(household_id),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["call_id"] == "provider-call-1"
    assert body["tracking_status"] == "recorded"
    assert events == [
        "consent",
        "persist_before_provider",
        "provider",
        "persist_provider_acceptance",
    ]


def test_live_call_requires_household_id(monkeypatch):
    monkeypatch.setattr("app.main.settings", production_call_settings())
    response = TestClient(app).post(
        "/api/v1/calls",
        headers={"Authorization": "Bearer call-token"},
        json={
            "to": "+919999999999",
            "callback_url": "https://example.test/callback",
            "consent": True,
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "household_id_required_for_live_call"


def test_outbound_call_rejects_invalid_or_overlong_phone_numbers():
    client = TestClient(app)
    for phone_number in ("++919999999999", "+1234567890123456"):
        response = client.post(
            "/api/v1/calls",
            json={
                "to": phone_number,
                "callback_url": "https://example.test/callback",
                "consent": True,
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "invalid_phone_number"

import asyncio
import base64
import hashlib
import hmac
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from app.main import app, _configured_telephony_callback_url


def test_configured_callback_requires_public_https(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "telephony_callback_url", "https://saathi.example.com/api/v1/webhooks/telephony")
    assert _configured_telephony_callback_url() == "https://saathi.example.com/api/v1/webhooks/telephony"


@pytest.mark.parametrize("url", [
    None,
    "http://saathi.example.com/webhook",
    "https://localhost/webhook",
    "https://127.0.0.1/webhook",
    "https://user:password@saathi.example.com/webhook",
])
def test_configured_callback_rejects_unsafe_or_missing_url(monkeypatch, url):
    import app.main as main

    monkeypatch.setattr(main.settings, "telephony_callback_url", url)
    with pytest.raises(Exception) as exc:
        _configured_telephony_callback_url()
    assert getattr(exc.value, "status_code", None) == 503


def test_signed_form_callback_updates_persistent_call_state(monkeypatch):
    import app.main as main

    secret = "test-webhook-secret"
    monkeypatch.setattr(main.settings, "telephony_webhook_secret", secret)
    monkeypatch.setattr(main.settings, "app_env", "production")
    monkeypatch.setattr(main.settings, "supabase_url", "https://project.supabase.co")
    monkeypatch.setattr(main.settings, "supabase_secret_key", "server-test-key")
    claimed = {}
    applied = {}

    async def record(**kwargs):
        claimed.update(kwargs)
        return False

    async def apply(self, **kwargs):
        applied.update(kwargs)
        return "completed"

    monkeypatch.setattr(main, "record_supabase_webhook_event", record)
    monkeypatch.setattr(main.SupabaseCallRepository, "apply_provider_status", apply)

    body = urlencode({"CallSid": "exotelCall123", "Status": "completed"}).encode()
    signature = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    response = TestClient(app).post(
        "/api/v1/webhooks/telephony",
        content=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Saathi-Signature": signature,
            # This header is not covered by the body signature and must not control deduplication.
            "X-Provider-Event-ID": "unsigned-spoofed-id",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "accepted"
    assert payload["call_status"] == "completed"
    assert payload["event_id"] == "sha256:" + hashlib.sha256(body).hexdigest()
    assert claimed["event_id"] == payload["event_id"]
    assert applied["provider_call_id"] == "exotelCall123"
    assert applied["provider_status"] == "completed"
    assert applied["provider_event_id"] == payload["event_id"]


def test_duplicate_signed_callback_is_reprocessed_for_recovery(monkeypatch):
    import app.main as main

    secret = "test-webhook-secret"
    monkeypatch.setattr(main.settings, "telephony_webhook_secret", secret)
    monkeypatch.setattr(main.settings, "app_env", "production")
    monkeypatch.setattr(main.settings, "supabase_url", "https://project.supabase.co")
    monkeypatch.setattr(main.settings, "supabase_secret_key", "server-test-key")
    processed = []

    async def record(**kwargs):
        return True

    async def apply(self, **kwargs):
        processed.append(kwargs["provider_event_id"])
        return "completed"

    monkeypatch.setattr(main, "record_supabase_webhook_event", record)
    monkeypatch.setattr(main.SupabaseCallRepository, "apply_provider_status", apply)

    body = urlencode({"CallSid": "exotelCall123", "Status": "completed"}).encode()
    signature = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    response = TestClient(app).post(
        "/api/v1/webhooks/telephony",
        content=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "X-Saathi-Signature": signature},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "duplicate"
    assert processed == ["sha256:" + hashlib.sha256(body).hexdigest()]

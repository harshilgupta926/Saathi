from app.webhook_events import InMemoryWebhookEventStore, derive_event_id


def test_event_id_is_deterministic_without_provider_id():
    assert derive_event_id(b"same-body") == derive_event_id(b"same-body")
    assert derive_event_id(b"same-body") != derive_event_id(b"other-body")


def test_provider_event_id_takes_precedence():
    assert derive_event_id(b"body", "evt-123") == "evt-123"


def test_store_detects_duplicates():
    store = InMemoryWebhookEventStore()
    assert store.seen_or_record("evt-123") is False
    assert store.seen_or_record("evt-123") is True


import asyncio

import pytest

from app.webhook_events import record_supabase_webhook_event


def test_durable_webhook_claim_returns_false_for_new_event(monkeypatch):
    class Response:
        status_code = 201
        is_success = True

    class Client:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers, json):
            assert url.endswith("/rest/v1/telephony_webhook_events")
            assert json["event_id"] == "evt-new"
            assert json["processing_status"] == "received"
            return Response()

    monkeypatch.setattr("app.webhook_events.httpx.AsyncClient", Client)
    duplicate = asyncio.run(record_supabase_webhook_event(
        base_url="https://project.supabase.co",
        secret_key="test-secret",
        event_id="evt-new",
        event_type="call.completed",
    ))
    assert duplicate is False


def test_durable_webhook_claim_treats_unique_conflict_as_duplicate(monkeypatch):
    class Response:
        status_code = 409
        is_success = False

    class Client:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers, json):
            return Response()

    monkeypatch.setattr("app.webhook_events.httpx.AsyncClient", Client)
    duplicate = asyncio.run(record_supabase_webhook_event(
        base_url="https://project.supabase.co",
        secret_key="test-secret",
        event_id="evt-old",
        event_type=None,
    ))
    assert duplicate is True


def test_durable_webhook_claim_fails_closed_on_server_error(monkeypatch):
    class Response:
        status_code = 500
        is_success = False

    class Client:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers, json):
            return Response()

    monkeypatch.setattr("app.webhook_events.httpx.AsyncClient", Client)
    with pytest.raises(RuntimeError, match="durable_webhook_store_http_500"):
        asyncio.run(record_supabase_webhook_event(
            base_url="https://project.supabase.co",
            secret_key="test-secret",
            event_id="evt-error",
            event_type=None,
        ))

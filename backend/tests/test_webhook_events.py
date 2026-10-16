from concurrent.futures import ThreadPoolExecutor

import pytest

from app.webhook_events import InMemoryWebhookEventStore, derive_event_id


def test_event_id_is_deterministic_without_provider_id():
    assert derive_event_id(b"same-body") == derive_event_id(b"same-body")
    assert derive_event_id(b"same-body") != derive_event_id(b"other-body")


def test_provider_event_id_takes_precedence():
    assert derive_event_id(b"body", " evt-123 ") == "evt-123"


def test_blank_provider_event_id_falls_back_to_body_digest():
    assert derive_event_id(b"body", "   ") == derive_event_id(b"body")


def test_store_detects_duplicates():
    store = InMemoryWebhookEventStore()
    assert store.seen_or_record("evt-123") is False
    assert store.seen_or_record(" evt-123 ") is True


def test_store_rejects_blank_event_id():
    with pytest.raises(ValueError, match="webhook_event_id_required"):
        InMemoryWebhookEventStore().seen_or_record("  ")


def test_in_memory_store_accepts_concurrent_event_once():
    store = InMemoryWebhookEventStore()
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(store.seen_or_record, ["evt-race"] * 64))
    assert results.count(False) == 1
    assert results.count(True) == 63


import asyncio

import pytest

from app.webhook_events import record_supabase_webhook_event


def test_durable_webhook_claim_returns_false_for_new_event(monkeypatch):
    class Response:
        status_code = 200
        is_success = True

        def json(self):
            return False

    class Client:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers, json):
            assert url.endswith("/rest/v1/rpc/saathi_record_webhook_event")
            assert json["p_event_id"] == "evt-new"
            assert json["p_event_type"] == "call.completed"
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
        status_code = 200
        is_success = True

        def json(self):
            return True

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

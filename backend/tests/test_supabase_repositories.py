import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.domain import Consent, ConsentType, Task, TaskStatus
from app.supabase_repositories import (
    SupabaseCallRepository,
    SupabaseConsentRepository,
    SupabaseRepositoryError,
    SupabaseTaskRepository,
)


class Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.is_success = 200 <= status_code < 300
        self.content = b"" if payload is None else b"json"

    def json(self):
        return self._payload


def fake_client(monkeypatch, responder):
    class Client:
        def __init__(self, timeout):
            assert timeout == 4.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def request(self, method, url, headers, json=None):
            return responder(method, url, headers, json)

    monkeypatch.setattr("app.supabase_repositories.httpx.AsyncClient", Client)


def configure(monkeypatch):
    monkeypatch.setattr(
        "app.supabase_repositories.get_settings",
        lambda: SimpleNamespace(
            supabase_url="https://example.supabase.co/",
            supabase_secret_key="server-test-key",
        ),
    )


def test_call_repository_persists_record_before_provider_acceptance(monkeypatch):
    configure(monkeypatch)
    household_id = "11111111-1111-4111-8111-111111111111"
    internal_call_id = "33333333-3333-4333-8333-333333333333"
    captured = {}

    def respond(method, url, headers, payload):
        captured.update(method=method, url=url, headers=headers, payload=payload)
        return Response([{"id": internal_call_id, "call_id": internal_call_id}], status_code=201)

    fake_client(monkeypatch, respond)
    call_id = asyncio.run(SupabaseCallRepository().create(
        household_id=household_id,
        phone_number="+919999999999",
        provider="exotel",
        language="hi",
    ))

    assert call_id == captured["payload"]["call_id"]
    assert captured["url"].endswith("/rest/v1/saathi_calls")
    assert captured["payload"]["household_id"] == household_id
    assert captured["payload"]["direction"] == "outbound"
    assert captured["payload"]["status"] == "connecting"
    assert captured["payload"]["phone_number"] == "+919999999999"


def test_consent_repository_saves_memory_consent_with_server_key(monkeypatch):
    configure(monkeypatch)
    household_id = "11111111-1111-4111-8111-111111111111"
    captured = {}

    def respond(method, url, headers, payload):
        captured.update(method=method, url=url, headers=headers, payload=payload)
        return Response([{"id": household_id}])

    fake_client(monkeypatch, respond)
    consent = Consent(
        household_id=household_id,
        consent_type=ConsentType.MEMORY,
        granted=True,
        recorded_at=datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc),
    )
    saved = asyncio.run(SupabaseConsentRepository().save(consent))

    assert saved == consent
    assert captured["method"] == "PATCH"
    assert captured["url"].endswith(f"/rest/v1/saathi_households?id=eq.{household_id}&select=id")
    assert captured["headers"]["Authorization"] == "Bearer server-test-key"
    assert captured["payload"]["memory_consent"] is True
    assert captured["payload"]["memory_consent_revoked_at"] is None


def test_consent_repository_treats_later_revocation_as_denial(monkeypatch):
    configure(monkeypatch)
    household_id = "11111111-1111-4111-8111-111111111111"
    fake_client(
        monkeypatch,
        lambda *args: Response([{
            "id": household_id,
            "memory_consent": True,
            "memory_consent_at": "2026-10-15T10:00:00Z",
            "memory_consent_revoked_at": "2026-10-15T10:05:00Z",
        }]),
    )

    consent = asyncio.run(SupabaseConsentRepository().get(
        household_id=household_id,
        consent_type=ConsentType.MEMORY,
    ))
    assert consent is not None
    assert consent.granted is False
    assert consent.recorded_at == datetime(2026, 10, 15, 10, 5, tzinfo=timezone.utc)


def test_task_repository_creates_task_and_keeps_database_id(monkeypatch):
    configure(monkeypatch)
    household_id = "11111111-1111-4111-8111-111111111111"
    task_id = "22222222-2222-4222-8222-222222222222"
    captured = {}

    def respond(method, url, headers, payload):
        captured.update(method=method, url=url, headers=headers, payload=payload)
        return Response([{
            "id": task_id,
            "household_id": household_id,
            "title": "Call back",
            "status": "pending",
            "missing_requirements": ["income certificate"],
            "scheduled_callback": None,
        }], status_code=201)

    fake_client(monkeypatch, respond)
    original = Task(
        household_id=household_id,
        title="Call back",
        missing_items=["income certificate"],
    )
    task = asyncio.run(SupabaseTaskRepository().create(original))

    assert task.task_id == task_id
    assert task.status == TaskStatus.PENDING
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/rest/v1/saathi_pending_tasks")
    assert captured["payload"]["household_id"] == household_id
    assert captured["payload"]["idempotency_key"] == original.idempotency_key
    assert captured["payload"]["idempotency_key"]


def test_task_repository_retries_idempotent_insert_by_fetching_existing_task(monkeypatch):
    configure(monkeypatch)
    household_id = "11111111-1111-4111-8111-111111111111"
    task_id = "22222222-2222-4222-8222-222222222222"
    task = Task(household_id=household_id, title="Call back")
    calls = []

    def respond(method, url, headers, payload):
        calls.append((method, url, payload))
        if method == "POST":
            assert payload["idempotency_key"] == task.idempotency_key
            return Response({"message": "unique conflict"}, status_code=409)
        assert f"idempotency_key=eq.{task.idempotency_key}" in url
        return Response([{
            "id": task_id,
            "household_id": household_id,
            "title": "Call back",
            "status": "pending",
            "missing_requirements": [],
            "scheduled_callback": None,
        }])

    fake_client(monkeypatch, respond)
    saved = asyncio.run(SupabaseTaskRepository().create(task))
    assert saved.task_id == task_id
    assert [item[0] for item in calls] == ["POST", "GET"]


def test_task_repository_scopes_updates_to_household(monkeypatch):
    configure(monkeypatch)
    household_id = "11111111-1111-4111-8111-111111111111"
    task_id = "22222222-2222-4222-8222-222222222222"
    captured = {}

    def respond(method, url, headers, payload):
        captured.update(method=method, url=url, payload=payload)
        return Response([{
            "id": task_id,
            "household_id": household_id,
            "title": "Call back",
            "status": "completed",
            "missing_requirements": [],
            "scheduled_callback": None,
        }])

    fake_client(monkeypatch, respond)
    task = asyncio.run(SupabaseTaskRepository().set_status(
        household_id=household_id,
        task_id=task_id,
        status=TaskStatus.COMPLETED,
    ))

    assert task.task_id == task_id
    assert task.status == TaskStatus.COMPLETED
    assert f"household_id=eq.{household_id}" in captured["url"]
    assert captured["payload"]["status"] == "completed"


def test_task_repository_rejects_cross_household_update(monkeypatch):
    configure(monkeypatch)
    fake_client(monkeypatch, lambda *args: Response([]))
    with pytest.raises(KeyError, match="task_not_found"):
        asyncio.run(SupabaseTaskRepository().set_status(
            household_id="11111111-1111-4111-8111-111111111111",
            task_id="22222222-2222-4222-8222-222222222222",
            status=TaskStatus.COMPLETED,
        ))


def test_persistence_fails_closed_when_secret_is_missing(monkeypatch):
    monkeypatch.setattr(
        "app.supabase_repositories.get_settings",
        lambda: SimpleNamespace(supabase_url="https://example.supabase.co", supabase_secret_key=None),
    )
    with pytest.raises(SupabaseRepositoryError, match="not_configured"):
        asyncio.run(SupabaseTaskRepository().list_open(
            household_id="11111111-1111-4111-8111-111111111111"
        ))


def test_consent_repository_does_not_accept_invalid_household_ids(monkeypatch):
    configure(monkeypatch)
    with pytest.raises(ValueError, match="valid_household_uuid_required"):
        asyncio.run(SupabaseConsentRepository().get(
            household_id="demo-household",
            consent_type=ConsentType.MEMORY,
        ))

import asyncio
from types import SimpleNamespace

from app.supabase_store import record_conversation_metadata


def test_conversation_metadata_uses_namespaced_table_and_minimal_payload(monkeypatch):
    captured = {}

    class Response:
        is_success = True
        status_code = 201

    class Client:
        def __init__(self, timeout):
            assert timeout == 3.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["payload"] = json
            return Response()

    monkeypatch.setattr(
        "app.supabase_store.get_settings",
        lambda: SimpleNamespace(
            supabase_url="https://nihdooom.supabase.co/",
            supabase_secret_key="server-test-key",
        ),
    )
    monkeypatch.setattr("app.supabase_store.httpx.AsyncClient", Client)

    result = asyncio.run(
        record_conversation_metadata(
            household_id="not-a-uuid-demo-id",
            agent_used="schemes",
            tools_called=["scheme_catalog"],
            confidence_score=0.9,
            language_code="hi",
            correlation_id="test-correlation",
            response_class="answered",
        )
    )

    assert result is True
    assert captured["url"] == "https://nihdooom.supabase.co/rest/v1/saathi_conversations"
    assert captured["headers"]["Authorization"] == "Bearer server-test-key"
    assert captured["payload"]["household_id"] is None
    assert captured["payload"]["agent_used"] == "schemes"
    assert "message" not in captured["payload"]
    assert "transcript" not in captured["payload"]
    assert "reply" not in captured["payload"]


def test_conversation_metadata_returns_false_when_supabase_is_not_configured(monkeypatch):
    monkeypatch.setattr(
        "app.supabase_store.get_settings",
        lambda: SimpleNamespace(supabase_url=None, supabase_secret_key=None),
    )
    result = asyncio.run(
        record_conversation_metadata(
            household_id=None,
            agent_used="schemes",
            tools_called=[],
            confidence_score=None,
            language_code="hi",
            correlation_id=None,
            response_class="answered",
        )
    )
    assert result is False

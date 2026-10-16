import asyncio

from app import provider_adapters


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    response = FakeResponse({})

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def request(self, *args, **kwargs):
        return self.response


def test_unknown_gemini_tool_is_ignored(monkeypatch):
    FakeClient.response = FakeResponse({
        "steps": [{"type": "function_call", "id": "x", "name": "delete_household", "arguments": {}}],
    })
    monkeypatch.setattr(provider_adapters.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(provider_adapters.GeminiToolRouter("key").choose("do something"))
    assert result is None


def test_malformed_gemini_arguments_are_ignored(monkeypatch):
    FakeClient.response = FakeResponse({
        "steps": [{"type": "function_call", "id": "x", "name": "get_weather", "arguments": "{bad"}],
    })
    monkeypatch.setattr(provider_adapters.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(provider_adapters.GeminiToolRouter("key").choose("weather"))
    assert result is None


def test_provider_retry_accepts_minimal_mock_response(monkeypatch):
    FakeClient.response = FakeResponse({
        "steps": [{
            "type": "function_call",
            "id": "x",
            "name": "get_weather",
            "arguments": {"latitude": 28.6, "longitude": 77.2},
        }],
    })
    monkeypatch.setattr(provider_adapters.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(provider_adapters.GeminiToolRouter("key").choose("weather"))
    assert result is not None
    assert result.name == "get_weather"


def test_model_cannot_force_human_escalation_for_general_intent():
    from types import SimpleNamespace
    from app.orchestrator import AgentContext, Orchestrator

    class Router:
        async def choose(self, _message):
            return SimpleNamespace(name="request_human", arguments={}, call_id="model-proposal")

    agent = Orchestrator()
    agent.reasoning_router = Router()
    outcome = asyncio.run(agent.handle("hello Saathi", AgentContext(household_id=None, language="en")))
    assert outcome.intent == "general"
    assert outcome.escalated is False
    assert outcome.tool_name != "request_human"


def test_model_human_escalation_is_allowed_after_deterministic_human_intent():
    from types import SimpleNamespace
    from app.orchestrator import AgentContext, Orchestrator

    class Router:
        async def choose(self, _message):
            return SimpleNamespace(name="request_human", arguments={}, call_id="model-proposal")

    agent = Orchestrator()
    agent.reasoning_router = Router()
    outcome = asyncio.run(agent.handle("मुझे किसी इंसान से बात करनी है", AgentContext(household_id=None, language="hi")))
    assert outcome.intent == "human"
    assert outcome.escalated is True

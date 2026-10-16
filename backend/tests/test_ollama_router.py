import asyncio

from app.provider_adapters import OllamaToolRouter


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    payload = {}

    def __init__(self, timeout):
        self.timeout = timeout
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json):
        self.calls.append((url, json))
        return FakeResponse(self.payload)


def test_ollama_router_returns_only_declared_tool(monkeypatch):
    import app.provider_adapters as adapters

    FakeClient.payload = {
        "message": {
            "tool_calls": [{
                "function": {
                    "name": "get_weather",
                    "arguments": {"latitude": 28.6, "longitude": 77.2},
                }
            }]
        }
    }
    monkeypatch.setattr(adapters.httpx, "AsyncClient", FakeClient)
    router = OllamaToolRouter("http://localhost:11434/", "qwen2.5:7b")
    result = asyncio.run(router.choose("Will it rain tomorrow?"))
    assert result.name == "get_weather"
    assert result.arguments["latitude"] == 28.6
    assert result.call_id == "ollama-local"


def test_ollama_router_returns_none_when_model_does_not_choose_tool(monkeypatch):
    import app.provider_adapters as adapters

    FakeClient.payload = {"message": {"content": "I am not sure.", "tool_calls": []}}
    monkeypatch.setattr(adapters.httpx, "AsyncClient", FakeClient)
    assert asyncio.run(OllamaToolRouter().choose("Tell me something uncertain")) is None


def test_ollama_router_ignores_undeclared_tool(monkeypatch):
    import app.provider_adapters as adapters

    FakeClient.payload = {
        "message": {"tool_calls": [{"function": {"name": "delete_household", "arguments": {}}}]}
    }
    monkeypatch.setattr(adapters.httpx, "AsyncClient", FakeClient)
    assert asyncio.run(OllamaToolRouter().choose("do something")) is None


def test_ollama_router_bounds_timeout_and_normalizes_url():
    router = OllamaToolRouter("http://localhost:11434///", timeout_seconds=999)
    assert router.base_url == "http://localhost:11434"
    assert router.timeout_seconds == 60.0



def test_ollama_router_default_matches_supported_local_stack_model():
    router = OllamaToolRouter()
    assert router.model == "qwen2.5:7b"


def test_ollama_provider_never_constructs_hosted_router_even_if_key_exists(monkeypatch):
    import app.orchestrator as orchestrator_module
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "llm_model", "qwen2.5:7b")
    monkeypatch.setattr(settings, "ollama_base_url", "http://127.0.0.1:11434")
    monkeypatch.setattr(settings, "gemini_api_key", "test-key-must-not-be-used")

    class LocalRouter:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    def forbidden_hosted_router(*_args, **_kwargs):
        raise AssertionError("Ollama configuration must never instantiate a hosted router")

    monkeypatch.setattr(orchestrator_module, "OllamaToolRouter", LocalRouter)
    monkeypatch.setattr(orchestrator_module, "GeminiToolRouter", forbidden_hosted_router)
    agent = orchestrator_module.Orchestrator()
    assert isinstance(agent.reasoning_router, LocalRouter)
    assert agent.reasoning_router.kwargs["model"] == "qwen2.5:7b"


def test_unavailable_ollama_falls_back_to_deterministic_routing_not_hosted_ai(monkeypatch):
    import httpx
    import app.orchestrator as orchestrator_module
    from app.config import get_settings
    from app.orchestrator import AgentContext

    settings = get_settings()
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "llm_model", "qwen2.5:7b")
    monkeypatch.setattr(settings, "ollama_base_url", "http://127.0.0.1:11434")
    monkeypatch.setattr(settings, "gemini_api_key", "test-key-must-not-be-used")

    class OfflineLocalRouter:
        async def choose(self, _message):
            raise httpx.ConnectError("local model unavailable")

    def forbidden_hosted_router(*_args, **_kwargs):
        raise AssertionError("Ollama failure must not trigger hosted AI")

    monkeypatch.setattr(orchestrator_module, "OllamaToolRouter", lambda **_kwargs: OfflineLocalRouter())
    monkeypatch.setattr(orchestrator_module, "GeminiToolRouter", forbidden_hosted_router)
    agent = orchestrator_module.Orchestrator()
    outcome = asyncio.run(agent.handle("hello Saathi", AgentContext(household_id=None, language="en")))
    assert outcome.intent == "general"
    assert outcome.reply

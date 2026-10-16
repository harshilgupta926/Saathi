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

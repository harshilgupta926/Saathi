import asyncio

from app.orchestrator import AgentContext, Orchestrator
from app.schemas import LocationContext


class FakeCall:
    def __init__(self, name: str, arguments: dict):
        self.name = name
        self.arguments = arguments


def test_reasoning_provider_can_select_declared_weather_tool(monkeypatch):
    from app import orchestrator as module

    class FakeSettings:
        demo_mode = False
        gemini_api_key = "test-key"
        llm_model = "test-model"
        mandi_api_key = None
        mandi_resource_id = None

    class FakeWeather:
        async def forecast(self, *, latitude, longitude):
            from app.provenance import ToolResult
            return ToolResult(ok=True, data={"temperature_c": 25, "rain_probability_pct": 70}, source=None)

    class FakeRouter:
        def __init__(self, *args, **kwargs):
            pass

        async def choose(self, message):
            return FakeCall("get_weather", {"latitude": 28.9931, "longitude": 77.0151})

    monkeypatch.setattr(module, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(module, "GeminiToolRouter", FakeRouter)
    monkeypatch.setattr(module, "OpenMeteoWeatherTool", lambda: FakeWeather())
    instance = Orchestrator()
    outcome = asyncio.run(instance.handle(
        "बारिश का हाल बताओ",
        AgentContext(household_id="h1", language="hi", location=LocationContext(latitude=28.9931, longitude=77.0151, label="Sonipat")),
    ))
    assert outcome.tool_name == "get_weather"
    assert outcome.result is not None and outcome.result.ok
    assert "बारिश" in outcome.reply


def test_reasoning_provider_cannot_execute_undeclared_capability(monkeypatch):
    from app import orchestrator as module

    class FakeSettings:
        demo_mode = False
        gemini_api_key = "test-key"
        llm_model = "test-model"
        mandi_api_key = None
        mandi_resource_id = None

    class FakeRouter:
        def __init__(self, *args, **kwargs):
            pass

        async def choose(self, message):
            return FakeCall("delete_household", {})

    monkeypatch.setattr(module, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(module, "GeminiToolRouter", FakeRouter)
    instance = Orchestrator()
    outcome = asyncio.run(instance.handle("मदद चाहिए", AgentContext(household_id="h1")))
    assert outcome.intent == "general"
    assert "नमस्ते" in outcome.reply

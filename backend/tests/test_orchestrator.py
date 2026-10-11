import asyncio

from app.orchestrator import AgentContext, Orchestrator
from app.schemas import LocationContext


def test_farming_weather_requires_explicit_location():
    outcome = asyncio.run(Orchestrator().handle("कल बारिश होगी?", AgentContext(household_id="h1")))
    assert outcome.intent == "farming"
    assert outcome.result is None
    assert "स्थान" in outcome.reply


def test_weather_uses_explicit_location_context():
    outcome = asyncio.run(Orchestrator().handle("कल बारिश होगी?", AgentContext(household_id="h1", location=LocationContext(latitude=28.61, longitude=77.21, label="Delhi"))))
    assert outcome.intent == "farming"
    assert outcome.result is not None and outcome.result.ok
    assert outcome.result.data["latitude"] == 28.61
    assert outcome.result.data["longitude"] == 77.21


def test_scheme_path_is_deterministic():
    outcome = asyncio.run(Orchestrator().handle("मुझे किसान योजना बताओ", AgentContext(household_id="h1")))
    assert outcome.intent == "scheme"
    assert "PM-KISAN" in outcome.reply
    assert outcome.escalated is False


def test_explicit_human_path_uses_policy():
    outcome = asyncio.run(Orchestrator().handle("मुझे किसी इंसान से बात करनी है", AgentContext(household_id="h1")))
    assert outcome.intent == "human"
    assert outcome.result is None
    assert outcome.escalated is True
    assert outcome.escalation_reason == "explicit_human_request"


def test_mandi_path_labels_demo_data():
    outcome = asyncio.run(Orchestrator().handle("सोनीपत मंडी में गेहूं का भाव", AgentContext(household_id="h1")))
    assert outcome.intent == "farming"
    assert outcome.result is not None and outcome.result.ok
    assert outcome.result.source is not None
    assert "DEMO DATA" in (outcome.result.source.freshness_note or "")


def test_mandi_without_live_configuration_is_not_presented_as_live(monkeypatch):
    from app import orchestrator as module
    class FakeSettings:
        demo_mode = False
        gemini_api_key = None
        llm_model = "test"
        mandi_api_key = None
        mandi_resource_id = None
        mandi_api_base = ""
    monkeypatch.setattr(module, "get_settings", lambda: FakeSettings())
    instance = module.Orchestrator()
    assert instance.mandi is None


def test_mandi_requires_entities_instead_of_using_demo_defaults():
    outcome = asyncio.run(Orchestrator().handle("मंडी का आज का भाव बताओ", AgentContext(household_id="h1")))
    assert outcome.intent == "farming"
    assert outcome.result is None
    assert "फसल" in outcome.reply


def test_farmer_scheme_uses_official_pmkisan_source():
    outcome = asyncio.run(Orchestrator().handle("मुझे किसान योजना बताओ", AgentContext(household_id="h1")))
    assert outcome.intent == "scheme"
    assert outcome.result is not None and outcome.result.ok
    assert outcome.result.source is not None
    assert "pmkisan.gov.in" in outcome.result.source.url
    assert outcome.tool_name == "get_pmkisan_info"


def test_combined_mandi_and_weather_returns_both_evidence_paths():
    outcome = asyncio.run(Orchestrator().handle(
        "सोनीपत में गेहूं का मंडी भाव और अगले 24 घंटे में बारिश का chance?",
        AgentContext(
            household_id="h1",
            location=LocationContext(latitude=28.9931, longitude=77.0151, label="Sonipat"),
        ),
    ))
    assert outcome.intent == "farming"
    assert outcome.tool_name == "get_mandi_price+get_weather"
    assert len(outcome.results) == 2
    assert all(result.source is not None for result in outcome.results)
    assert "मॉडल भाव" in outcome.reply
    assert "बारिश" in outcome.reply


def test_combined_request_requires_all_mandi_entities():
    outcome = asyncio.run(Orchestrator().handle(
        "गेहूं का मंडी भाव और कल बारिश होगी?",
        AgentContext(
            household_id="h1",
            location=LocationContext(latitude=28.9931, longitude=77.0151, label="Sonipat"),
        ),
    ))
    assert outcome.result is None
    assert "राज्य" in outcome.reply or "जिला" in outcome.reply


def test_human_request_is_not_downgraded_by_agent_word():
    outcome = asyncio.run(Orchestrator().handle("मुझे agent नहीं, इंसान चाहिए", AgentContext(household_id="h1")))
    assert outcome.intent == "human"
    assert outcome.escalated is True


def test_tool_policy_rejects_cross_intent_capability():
    from app.orchestrator import ToolPolicy
    assert ToolPolicy.permits("farming", "get_weather") is True
    assert ToolPolicy.permits("scheme", "get_weather") is False
    assert ToolPolicy.permits("general", "get_mandi_price") is False


def test_combined_provider_failure_does_not_invent_missing_value(monkeypatch):
    from app import orchestrator as module
    async def failed_weather(*, latitude, longitude):
        from app.provenance import ToolResult
        return ToolResult(ok=False, error_code="WEATHER_PROVIDER_ERROR")
    instance = module.Orchestrator()
    monkeypatch.setattr(instance.weather, "forecast", failed_weather)
    outcome = asyncio.run(instance.handle(
        "सोनीपत में गेहूं का मंडी भाव और बारिश का chance?",
        AgentContext(
            household_id="h1",
            location=LocationContext(latitude=28.9931, longitude=77.0151, label="Sonipat"),
        ),
    ))
    assert "मौसम की जानकारी अभी उपलब्ध नहीं है" in outcome.reply
    assert outcome.escalated is True

def test_weather_phrase_with_sambhavana_does_not_trigger_mandi():
    outcome = asyncio.run(Orchestrator().handle(
        "अगले 24 घंटे में बारिश की संभावना कितनी है?",
        AgentContext(
            household_id="h1",
            location=LocationContext(latitude=28.9931, longitude=77.0151, label="Sonipat"),
        ),
    ))
    assert outcome.tool_name == "get_weather"
    assert outcome.result is not None and outcome.result.ok
    assert outcome.result.data["rain_probability_pct"] == 20


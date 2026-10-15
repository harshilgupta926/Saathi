import asyncio

from app.orchestrator import AgentContext, Orchestrator


def test_pmfby_request_uses_official_catalogue_and_caveats():
    outcome = asyncio.run(
        Orchestrator().handle(
            "मुझे PMFBY फसल बीमा योजना बताओ",
            AgentContext(household_id="demo-household"),
        )
    )
    assert outcome.intent == "scheme"
    assert outcome.tool_name == "get_scheme_catalog"
    assert outcome.result is not None and outcome.result.ok
    assert outcome.result.data["scheme_id"] == "pmfby"
    assert outcome.result.source is not None
    assert "pmfby.gov.in" in outcome.result.source.url
    assert "state" in outcome.reply.lower() or "राज्य" in outcome.reply
    assert "अंतिम पात्रता" in outcome.reply


def test_pmkisan_request_uses_catalogue_record():
    outcome = asyncio.run(
        Orchestrator().handle(
            "PM Kisan yojana eligibility बताओ",
            AgentContext(household_id="demo-household"),
        )
    )
    assert outcome.intent == "scheme"
    assert outcome.tool_name == "get_pmkisan_info"
    assert outcome.result is not None and outcome.result.ok
    assert outcome.result.data["scheme_id"] == "pm-kisan"
    assert outcome.result.data["source_checked_on"] == "2026-10-15"
    assert "pmkisan.gov.in" in outcome.result.source.url

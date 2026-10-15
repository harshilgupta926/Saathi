from pathlib import Path


def test_dashboard_is_explicit_about_prototype_only_memory_consent():
    source = Path(__file__).parents[2].joinpath("frontend/app/dashboard/page.tsx").read_text(encoding="utf-8")
    assert "Household memory is disabled in this prototype" in source
    assert "No consent is being collected or stored here" in source
    # Do not present an in-memory toggle as if it granted durable consent.
    assert "memoryConsent" not in source
    assert "setMemoryConsent" not in source
    assert "reminderConsent" not in source
    assert "followUpStatus" not in source
    assert "simulateThreeDaysLater" not in source

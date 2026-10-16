from pathlib import Path


def test_dashboard_distinguishes_consent_from_automatic_memory_storage():
    source = Path(__file__).parents[2].joinpath("frontend/app/dashboard/page.tsx").read_text(encoding="utf-8")
    assert "Grant permission for future household-memory storage" in source
    assert "The conversation workflow does not yet write memories automatically" in source
    assert "memoryConsent" not in source
    assert "setMemoryConsent" not in source
    assert "reminderConsent" not in source
    assert "followUpStatus" not in source
    assert "simulateThreeDaysLater" not in source

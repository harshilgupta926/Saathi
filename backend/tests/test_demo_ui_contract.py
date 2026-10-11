from pathlib import Path


def test_dashboard_is_explicit_about_prototype_only_memory_consent():
    source = Path(__file__).parents[2].joinpath("frontend/app/dashboard/page.tsx").read_text(encoding="utf-8")
    assert "memoryConsent" in source
    assert "Household memory is intentionally not active in this prototype" in source
    assert "consent, opt-out, quiet hours and deletion must be persisted server-side" in source
    # These are intentionally not presented as working controls until durable
    # backend persistence and dispatcher workflows actually exist.
    assert "reminderConsent" not in source
    assert "followUpStatus" not in source
    assert "simulateThreeDaysLater" not in source

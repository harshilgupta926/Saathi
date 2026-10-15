from datetime import date
from app.scheme_freshness import assess_scheme_freshness


def test_recent_review_is_reviewed_not_live():
    result = assess_scheme_freshness("2026-10-11", today=date(2026, 10, 15))
    assert result.status == "reviewed"
    assert result.age_days == 4


def test_old_review_is_stale():
    result = assess_scheme_freshness("2026-08-01", today=date(2026, 10, 15))
    assert result.status == "stale"
    assert result.age_days == 75


def test_missing_invalid_and_future_dates_are_unknown():
    assert assess_scheme_freshness(None, today=date(2026, 10, 15)).status == "unknown"
    assert assess_scheme_freshness("not-a-date", today=date(2026, 10, 15)).status == "unknown"
    assert assess_scheme_freshness("2026-10-16", today=date(2026, 10, 15)).status == "unknown"

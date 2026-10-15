from datetime import datetime, timezone
from app.market_freshness import assess_mandi_freshness


NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)


def test_recent_observation_is_current():
    result = assess_mandi_freshness(datetime(2026, 10, 12, tzinfo=timezone.utc), now=NOW)
    assert result.status == "current"
    assert result.age_days == 3


def test_old_observation_is_stale():
    result = assess_mandi_freshness(datetime(2026, 10, 1, tzinfo=timezone.utc), now=NOW)
    assert result.status == "stale"


def test_missing_or_invalid_observation_date_is_unknown():
    assert assess_mandi_freshness(None, now=NOW).status == "unknown"
    assert assess_mandi_freshness(datetime.min.replace(tzinfo=timezone.utc), now=NOW).status == "unknown"


def test_future_observation_date_is_not_current():
    assert assess_mandi_freshness(datetime(2026, 10, 16, tzinfo=timezone.utc), now=NOW).status == "future"

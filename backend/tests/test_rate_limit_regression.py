from app import rate_limit


def test_limiter_enforces_per_key_limit_and_recovers_after_window(monkeypatch):
    now = 100.0
    monkeypatch.setattr(rate_limit, "monotonic", lambda: now)
    limiter = rate_limit.InMemoryRateLimiter(limit=2, window_seconds=10, max_keys=10)

    assert limiter.allow("household-a") is True
    assert limiter.allow("household-a") is True
    assert limiter.allow("household-a") is False

    now += 10.1
    assert limiter.allow("household-a") is True


def test_limiter_keeps_buckets_isolated_between_keys(monkeypatch):
    monkeypatch.setattr(rate_limit, "monotonic", lambda: 100.0)
    limiter = rate_limit.InMemoryRateLimiter(limit=1, window_seconds=60, max_keys=10)

    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is False
    assert limiter.allow("client-b") is True


def test_limiter_evicts_oldest_bucket_when_capacity_is_reached(monkeypatch):
    now = 100.0
    monkeypatch.setattr(rate_limit, "monotonic", lambda: now)
    limiter = rate_limit.InMemoryRateLimiter(limit=1, window_seconds=60, max_keys=2)

    assert limiter.allow("old-client") is True
    now += 1
    assert limiter.allow("recent-client") is True
    now += 1

    # A third key forces bounded-memory eviction of the least recently active bucket.
    assert limiter.allow("new-client") is True
    assert len(limiter._events) == 2
    assert "old-client" not in limiter._events
    assert "recent-client" in limiter._events
    assert "new-client" in limiter._events


def test_limiter_rejects_non_positive_configuration():
    import pytest

    with pytest.raises(ValueError, match="rate_limiter_configuration_must_be_positive"):
        rate_limit.InMemoryRateLimiter(limit=0)
    with pytest.raises(ValueError, match="rate_limiter_configuration_must_be_positive"):
        rate_limit.InMemoryRateLimiter(window_seconds=0)
    with pytest.raises(ValueError, match="rate_limiter_configuration_must_be_positive"):
        rate_limit.InMemoryRateLimiter(max_keys=0)

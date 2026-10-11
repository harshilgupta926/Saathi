from datetime import datetime, timezone

from app.callback_policy import evaluate_callback_eligibility


def test_callback_requires_current_outbound_consent():
    decision = evaluate_callback_eligibility(
        consent_granted=False,
        consent_revoked=False,
        scheduled_at=datetime(2026, 10, 10, 8, tzinfo=timezone.utc),
        status="pending",
        attempt_count=0,
        now=datetime(2026, 10, 10, 10, tzinfo=timezone.utc),
    )
    assert not decision.allowed
    assert decision.reason == "outbound_consent_missing_or_revoked"


def test_revoked_consent_blocks_even_if_task_is_due():
    decision = evaluate_callback_eligibility(
        consent_granted=True,
        consent_revoked=True,
        scheduled_at=datetime(2026, 10, 10, 8, tzinfo=timezone.utc),
        status="pending",
        attempt_count=0,
        now=datetime(2026, 10, 10, 10, tzinfo=timezone.utc),
    )
    assert not decision.allowed


def test_future_callback_is_not_due():
    decision = evaluate_callback_eligibility(
        consent_granted=True,
        consent_revoked=False,
        scheduled_at=datetime(2026, 10, 10, 12, tzinfo=timezone.utc),
        status="scheduled",
        attempt_count=0,
        now=datetime(2026, 10, 10, 10, tzinfo=timezone.utc),
    )
    assert not decision.allowed
    assert decision.reason == "callback_not_due"


def test_callback_in_quiet_hours_is_blocked():
    decision = evaluate_callback_eligibility(
        consent_granted=True,
        consent_revoked=False,
        scheduled_at=datetime(2026, 10, 10, 15, tzinfo=timezone.utc),
        status="pending",
        attempt_count=0,
        now=datetime(2026, 10, 10, 16, tzinfo=timezone.utc),  # 21:30 in India
    )
    assert not decision.allowed
    assert decision.reason == "quiet_hours"


def test_attempt_limit_blocks_repeated_dispatch():
    decision = evaluate_callback_eligibility(
        consent_granted=True,
        consent_revoked=False,
        scheduled_at=datetime(2026, 10, 10, 8, tzinfo=timezone.utc),
        status="pending",
        attempt_count=3,
        now=datetime(2026, 10, 10, 10, tzinfo=timezone.utc),
    )
    assert not decision.allowed
    assert decision.reason == "callback_attempt_limit_reached"


def test_valid_due_callback_is_allowed_outside_quiet_hours():
    decision = evaluate_callback_eligibility(
        consent_granted=True,
        consent_revoked=False,
        scheduled_at=datetime(2026, 10, 10, 8, tzinfo=timezone.utc),
        status="pending",
        attempt_count=0,
        now=datetime(2026, 10, 10, 10, tzinfo=timezone.utc),  # 15:30 in India
    )
    assert decision.allowed
    assert decision.reason == "eligible"


def test_invalid_timezone_fails_closed():
    decision = evaluate_callback_eligibility(
        consent_granted=True,
        consent_revoked=False,
        scheduled_at=datetime(2026, 10, 10, 8, tzinfo=timezone.utc),
        status="pending",
        attempt_count=0,
        now=datetime(2026, 10, 10, 10, tzinfo=timezone.utc),
        timezone_name="Not/A-Timezone",
    )
    assert not decision.allowed
    assert decision.reason == "invalid_timezone_configuration"

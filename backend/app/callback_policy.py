"""Pure policy checks for a future durable callback dispatcher.

This module does not place calls. The worker must load the current household consent
and task state from trusted persistence immediately before invoking the telephony
provider, then atomically claim the task to prevent duplicate dispatch.
"""
from dataclasses import dataclass
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class CallbackDecision:
    allowed: bool
    reason: str


def evaluate_callback_eligibility(
    *,
    consent_granted: bool,
    consent_revoked: bool,
    scheduled_at: datetime | None,
    status: str,
    attempt_count: int,
    now: datetime | None = None,
    timezone_name: str = "Asia/Kolkata",
    quiet_start: time = time(21, 0),
    quiet_end: time = time(8, 0),
    max_attempts: int = 3,
) -> CallbackDecision:
    """Fail closed unless a callback is consented, due, retryable and outside quiet hours."""
    if not consent_granted or consent_revoked:
        return CallbackDecision(False, "outbound_consent_missing_or_revoked")
    if scheduled_at is None:
        return CallbackDecision(False, "callback_not_scheduled")
    if status not in {"pending", "scheduled"}:
        return CallbackDecision(False, "task_not_dispatchable")
    if attempt_count < 0 or max_attempts < 1 or attempt_count >= max_attempts:
        return CallbackDecision(False, "callback_attempt_limit_reached")

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    due = scheduled_at if scheduled_at.tzinfo else scheduled_at.replace(tzinfo=timezone.utc)
    if due > current:
        return CallbackDecision(False, "callback_not_due")

    try:
        local_now = current.astimezone(ZoneInfo(timezone_name))
    except ZoneInfoNotFoundError:
        return CallbackDecision(False, "invalid_timezone_configuration")

    local_time = local_now.timetz().replace(tzinfo=None)
    if quiet_start == quiet_end:
        in_quiet_hours = False
    elif quiet_start < quiet_end:
        in_quiet_hours = quiet_start <= local_time < quiet_end
    else:
        in_quiet_hours = local_time >= quiet_start or local_time < quiet_end
    if in_quiet_hours:
        return CallbackDecision(False, "quiet_hours")

    return CallbackDecision(True, "eligible")

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class MandiFreshness:
    status: str
    age_days: int | None


def assess_mandi_freshness(observation: datetime | None, *, now: datetime | None = None, max_age_days: int = 7) -> MandiFreshness:
    """Classify a market observation date; retrieval time is never substituted for it."""
    if observation is None or observation.year < 2000:
        return MandiFreshness("unknown", None)
    now = now or datetime.now(timezone.utc)
    if observation.tzinfo is None:
        observation = observation.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    age = (now.astimezone(timezone.utc).date() - observation.astimezone(timezone.utc).date()).days
    if age < 0:
        return MandiFreshness("future", age)
    if age > max_age_days:
        return MandiFreshness("stale", age)
    return MandiFreshness("current", age)

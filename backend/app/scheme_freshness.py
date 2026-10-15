from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class SchemeFreshness:
    status: str
    age_days: int | None


def assess_scheme_freshness(reviewed_on: str | None, *, today: date | None = None, max_age_days: int = 30) -> SchemeFreshness:
    """Classify catalogue review recency; this does not certify current eligibility."""
    today = today or date.today()
    if not reviewed_on:
        return SchemeFreshness("unknown", None)
    try:
        reviewed = date.fromisoformat(str(reviewed_on).strip())
    except (TypeError, ValueError):
        return SchemeFreshness("unknown", None)
    if reviewed > today:
        return SchemeFreshness("unknown", None)
    age = (today - reviewed).days
    return SchemeFreshness("stale" if age > max_age_days else "reviewed", age)

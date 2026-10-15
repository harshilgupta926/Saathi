from dataclasses import replace

from app.orchestrator import _catalogue_scheme_response
from app.scheme_catalog import get_scheme


def test_static_scheme_catalogue_is_not_reported_as_live_retrieval():
    scheme = get_scheme("pm-kisan")
    assert scheme is not None
    _, result = _catalogue_scheme_response(scheme)
    assert result.source is not None
    assert result.source.retrieved_at is None
    assert result.source.freshness_status == "reviewed"
    assert result.data["source_retrieved_live"] is False
    assert "not a live government lookup" in (result.source.freshness_note or "")


def test_invalid_review_date_is_not_marked_fresh():
    scheme = get_scheme("pm-kisan")
    assert scheme is not None
    _, result = _catalogue_scheme_response(replace(scheme, source_checked_on="invalid-date"))
    assert result.source is not None
    assert result.source.retrieved_at is None
    assert result.source.freshness_status == "unknown"

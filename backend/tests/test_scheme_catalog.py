from app.scheme_catalog import get_scheme, list_schemes


def test_catalog_has_unique_stable_ids_and_official_sources():
    schemes = list_schemes()
    ids = [item.scheme_id for item in schemes]
    assert len(ids) == len(set(ids))
    assert {"pm-kisan", "pmfby"} <= set(ids)
    for item in schemes:
        assert item.source_url.startswith("https://")
        assert item.application_url.startswith("https://")
        assert item.source_checked_on == "2026-10-11"
        assert item.review_note


def test_pm_kisan_record_is_source_backed_and_cautious_about_eligibility():
    scheme = get_scheme(" PM-KISAN ")
    assert scheme is not None
    assert "₹6,000" in scheme.summary
    assert any("State/UT" in note for note in scheme.eligibility_notes)
    assert "pmkisan.gov.in" in scheme.application_url


def test_pmfby_record_warns_that_rules_depend_on_state_and_season():
    scheme = get_scheme("pmfby")
    assert scheme is not None
    assert any("state" in note.casefold() and "season" in note.casefold() for note in scheme.eligibility_notes)
    assert "pmfby.gov.in" in scheme.application_url


def test_unknown_scheme_is_not_guessed():
    assert get_scheme("made-up-scheme") is None

from fastapi.testclient import TestClient

from app.main import app


def test_scheme_catalog_endpoint_lists_official_source_and_caveat():
    response = TestClient(app).get("/api/v1/schemes")
    assert response.status_code == 200
    payload = response.json()
    assert {item["scheme_id"] for item in payload["schemes"]} >= {"pm-kisan", "pmfby"}
    assert "eligibility" in payload["notice"].lower()
    for item in payload["schemes"]:
        assert item["source_url"].startswith("https://")
        assert item["application_url"].startswith("https://")
        assert item["source_checked_on"]


def test_scheme_detail_endpoint_returns_record_and_unknown_is_404():
    client = TestClient(app)
    found = client.get("/api/v1/schemes/pm-kisan")
    missing = client.get("/api/v1/schemes/not-a-real-scheme")
    assert found.status_code == 200
    assert found.json()["scheme_id"] == "pm-kisan"
    assert missing.status_code == 404
    assert missing.json()["detail"] == "scheme_not_found"

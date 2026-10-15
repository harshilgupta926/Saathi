from fastapi.testclient import TestClient
from fastapi import HTTPException
import pytest

from app.main import app, _authorize_api_request, _authorize_telephony_stream


def test_api_auth_fails_closed_when_production_token_missing(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", False)
    monkeypatch.setattr(main.settings, "app_env", "production")
    monkeypatch.setattr(main.settings, "api_auth_token", None)
    with pytest.raises(HTTPException) as exc:
        _authorize_api_request(None)
    assert exc.value.status_code == 503
    assert exc.value.detail == "api_authentication_not_configured"


def test_api_auth_rejects_wrong_token_and_accepts_matching_token(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", False)
    monkeypatch.setattr(main.settings, "app_env", "production")
    monkeypatch.setattr(main.settings, "api_auth_token", "test-secret")
    with pytest.raises(HTTPException) as exc:
        _authorize_api_request("wrong")
    assert exc.value.status_code == 401
    _authorize_api_request("test-secret")


def test_text_api_requires_auth_in_production(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", False)
    monkeypatch.setattr(main.settings, "app_env", "production")
    monkeypatch.setattr(main.settings, "api_auth_token", "test-secret")
    client = TestClient(app)
    payload = {"message": "नमस्ते", "language": "hi"}
    assert client.post("/api/v1/agent", json=payload).status_code == 401
    assert client.post("/api/v1/agent", json=payload, headers={"X-Saathi-API-Key": "wrong"}).status_code == 401
    assert client.post("/api/v1/agent", json=payload, headers={"X-Saathi-API-Key": "test-secret"}).status_code == 200


def test_telephony_stream_auth_fails_closed_in_production(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", False)
    monkeypatch.setattr(main.settings, "app_env", "production")
    monkeypatch.setattr(main.settings, "telephony_stream_token", None)
    with pytest.raises(HTTPException) as exc:
        _authorize_telephony_stream(None)
    assert exc.value.status_code == 503
    assert exc.value.detail == "telephony_stream_auth_not_configured"


def test_telephony_stream_rejects_wrong_token_and_accepts_matching_token(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", False)
    monkeypatch.setattr(main.settings, "app_env", "production")
    monkeypatch.setattr(main.settings, "telephony_stream_token", "stream-secret")
    with pytest.raises(HTTPException) as exc:
        _authorize_telephony_stream("wrong")
    assert exc.value.status_code == 401
    _authorize_telephony_stream("stream-secret")


def test_local_demo_mode_does_not_require_operator_tokens(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", True)
    monkeypatch.setattr(main.settings, "app_env", "development")
    monkeypatch.setattr(main.settings, "api_auth_token", None)
    monkeypatch.setattr(main.settings, "telephony_stream_token", None)
    _authorize_api_request(None)
    _authorize_telephony_stream(None)


def test_readiness_fails_closed_when_production_auth_is_missing(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", False)
    monkeypatch.setattr(main.settings, "app_env", "production")
    monkeypatch.setattr(main.settings, "api_auth_token", None)
    response = TestClient(app).get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "not_ready"
    assert response.json()["missing_requirements"] == ["api_operator_auth"]
    assert response.json()["provider_contracts"]["api_operator_auth"] is False


def test_readiness_allows_local_demo_without_operator_token(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", True)
    monkeypatch.setattr(main.settings, "app_env", "development")
    monkeypatch.setattr(main.settings, "api_auth_token", None)
    response = TestClient(app).get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["missing_requirements"] == []

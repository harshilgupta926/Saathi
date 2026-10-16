from fastapi.testclient import TestClient

from app.main import app


PNG = b"\x89PNG\r\n\x1a\n" + b"fixture"


def test_local_ocr_endpoint_uses_local_provider_and_returns_review_metadata(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", True)
    monkeypatch.setattr(main.settings, "app_env", "development")
    monkeypatch.setattr(main.settings, "local_ocr_enabled", True)
    seen = {}

    def fake_ocr(content, **kwargs):
        seen["content"] = content
        seen["kwargs"] = kwargs
        return {
            "text": "Kisan Card",
            "engine": "tesseract-local",
            "language": kwargs["language"],
            "average_confidence": 91.0,
            "needs_human_review": False,
            "network_used": False,
        }

    monkeypatch.setattr(main, "extract_local_ocr", fake_ocr)
    response = TestClient(app).post(
        "/api/v1/documents/ocr",
        files={"file": ("card.png", PNG, "image/png")},
        data={"language": "hin+eng"},
    )
    assert response.status_code == 200
    assert response.json()["text"] == "Kisan Card"
    assert response.json()["network_used"] is False
    assert seen["content"] == PNG
    assert seen["kwargs"]["language"] == "hin+eng"


def test_local_ocr_endpoint_rejects_oversized_upload_before_processing(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", True)
    monkeypatch.setattr(main.settings, "app_env", "development")
    monkeypatch.setattr(main.settings, "local_ocr_enabled", True)
    monkeypatch.setattr(main.settings, "local_ocr_max_bytes", 4)
    response = TestClient(app).post(
        "/api/v1/documents/ocr",
        files={"file": ("card.png", PNG, "image/png")},
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "document_too_large"


def test_local_ocr_endpoint_is_disabled_by_configuration(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", True)
    monkeypatch.setattr(main.settings, "app_env", "development")
    monkeypatch.setattr(main.settings, "local_ocr_enabled", False)
    response = TestClient(app).post(
        "/api/v1/documents/ocr",
        files={"file": ("card.png", PNG, "image/png")},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "local_ocr_disabled"

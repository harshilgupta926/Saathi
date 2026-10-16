import subprocess

import pytest

from app import local_ocr


PNG = b"\x89PNG\r\n\x1a\n" + b"fixture"


def test_local_ocr_parses_text_and_confidence_without_network(monkeypatch):
    monkeypatch.setattr(local_ocr.shutil, "which", lambda name: "/usr/bin/tesseract")
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["input"] = kwargs["input"]
        captured["timeout"] = kwargs["timeout"]
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
                "5\t1\t1\t1\t1\t1\t0\t0\t20\t10\t91.5\tKisan\n"
                "5\t1\t1\t1\t1\t2\t20\t0\t20\t10\t88.5\tCard\n"
            ).encode("utf-8"),
            stderr=b"",
        )

    monkeypatch.setattr(local_ocr.subprocess, "run", fake_run)
    result = local_ocr.extract_local_ocr(PNG, content_type="image/png")
    assert result["text"] == "Kisan Card"
    assert result["average_confidence"] == 90.0
    assert result["needs_human_review"] is False
    assert result["network_used"] is False
    assert captured["input"] == PNG
    assert captured["timeout"] == 15.0
    assert "shell" not in captured


def test_local_ocr_rejects_mime_spoof_and_oversized_upload():
    with pytest.raises(ValueError, match="unsupported_or_invalid_image"):
        local_ocr.extract_local_ocr(b"not an image", content_type="image/png")
    with pytest.raises(ValueError, match="document_too_large"):
        local_ocr.extract_local_ocr(PNG, content_type="image/png", max_bytes=4)


def test_local_ocr_fails_clearly_when_engine_missing(monkeypatch):
    monkeypatch.setattr(local_ocr.shutil, "which", lambda name: None)
    with pytest.raises(local_ocr.LocalOCRError, match="local_ocr_engine_unavailable"):
        local_ocr.extract_local_ocr(PNG, content_type="image/png")


def test_local_ocr_timeout_is_bounded(monkeypatch):
    monkeypatch.setattr(local_ocr.shutil, "which", lambda name: "/usr/bin/tesseract")

    def timeout_run(command, **kwargs):
        assert kwargs["timeout"] == 20.0
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(local_ocr.subprocess, "run", timeout_run)
    with pytest.raises(local_ocr.LocalOCRError, match="local_ocr_timeout"):
        local_ocr.extract_local_ocr(PNG, content_type="image/png", timeout_seconds=500)


def test_local_ocr_rejects_invalid_language(monkeypatch):
    monkeypatch.setattr(local_ocr.shutil, "which", lambda name: "/usr/bin/tesseract")
    with pytest.raises(ValueError, match="invalid_ocr_language"):
        local_ocr.extract_local_ocr(PNG, content_type="image/png", language="hin;rm -rf /")

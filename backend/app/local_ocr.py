"""Offline OCR through a locally installed Tesseract binary.

This module deliberately has no network client and never uploads document bytes.
"""
import csv
import io
import re
import shutil
import subprocess
from typing import Any


MAX_OCR_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/tiff"}
_LANGUAGE_RE = re.compile(r"^[a-z]{3}(?:\+[a-z]{3}){0,2}$")


class LocalOCRError(RuntimeError):
    """Safe, non-sensitive local OCR failure."""


def _has_image_signature(content: bytes, content_type: str) -> bool:
    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if content_type == "image/webp":
        return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    if content_type == "image/tiff":
        return content.startswith((b"II*\x00", b"MM\x00*"))
    return False


def extract_local_ocr(
    content: bytes,
    *,
    content_type: str,
    language: str = "hin+eng",
    timeout_seconds: float = 15.0,
    max_bytes: int = MAX_OCR_BYTES,
    binary: str = "tesseract",
) -> dict[str, Any]:
    """Extract text and word-confidence metadata from a bounded image, fully locally."""
    if not content:
        raise ValueError("document_content_empty")
    if len(content) > min(max_bytes, MAX_OCR_BYTES):
        raise ValueError("document_too_large")
    if content_type not in ALLOWED_IMAGE_TYPES or not _has_image_signature(content, content_type):
        raise ValueError("unsupported_or_invalid_image")
    if not _LANGUAGE_RE.fullmatch(language):
        raise ValueError("invalid_ocr_language")
    executable = shutil.which(binary)
    if not executable:
        raise LocalOCRError("local_ocr_engine_unavailable")

    try:
        result = subprocess.run(
            [executable, "stdin", "stdout", "-l", language, "--psm", "3", "tsv"],
            input=content,
            capture_output=True,
            timeout=max(1.0, min(float(timeout_seconds), 20.0)),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise LocalOCRError("local_ocr_timeout") from exc
    except OSError as exc:
        raise LocalOCRError("local_ocr_execution_failed") from exc

    if result.returncode != 0:
        raise LocalOCRError("local_ocr_execution_failed")

    words: list[str] = []
    confidences: list[float] = []
    try:
        stdout = result.stdout.decode("utf-8", errors="replace") if isinstance(result.stdout, bytes) else str(result.stdout or "")
        rows = csv.DictReader(io.StringIO(stdout), delimiter="\t")
        for row in rows:
            word = (row.get("text") or "").strip()
            if not word:
                continue
            words.append(word)
            try:
                confidence = float(row.get("conf", "-1"))
            except (TypeError, ValueError):
                continue
            if confidence >= 0:
                confidences.append(confidence)
    except (csv.Error, TypeError) as exc:
        raise LocalOCRError("local_ocr_invalid_output") from exc

    average_confidence = round(sum(confidences) / len(confidences), 2) if confidences else None
    return {
        "text": " ".join(words),
        "engine": "tesseract-local",
        "language": language,
        "average_confidence": average_confidence,
        "needs_human_review": not words or average_confidence is None or average_confidence < 75.0,
        "network_used": False,
    }

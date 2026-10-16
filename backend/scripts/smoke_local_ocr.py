#!/usr/bin/env python3
"""Real offline Hindi+English Tesseract smoke test using a synthetic fixture."""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

for candidate in (Path("/app"), Path(__file__).resolve().parent.parent, Path(__file__).resolve().parent.parent.parent / "backend"):
    if (candidate / "app" / "local_ocr.py").is_file():
        sys.path.insert(0, str(candidate))
        break
from app.local_ocr import extract_local_ocr

# Synthetic, non-personal 560x150 PNG: "किसान कार्ड" / "Kisan Card".
_FIXTURE_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAjAAAACWAQAAAADoUI8YAAACoUlEQVR42u3ZPW7bMBTA8T9lAdYQxBozNLV6A48ZDEfI1GP4CBkzuUwRtGNzgQI+RocAVdIhHjrkCErtISMdZJAL2a+D/AW3Q/WaIQWoyXqAfyD5HimQNMJzPAGe8YxnVsws2g3OYwXzMNsNloWCybE7wSJSMI1yuBOcOgXzveH+edwDgLPnSXh3JxjrmNc7wYWOiZ+jU0c0d4LN+o5s9+BdvnSk5vOypiYit1KIjMvBsYxFpC2fpHyn7dT+i1m2tpeX9wChinnaGikLzHWtcUx4XE2DuaXUMWP3eZ6CmIRy8DRctqnWEwIhtsiXE9Keiz5T3XC+Gtam1TMnGRC0ciA6ghMlY4NuuFmywq9WxRQwLjAAAgRkGqZ0GAdYYABMB7mGOUwq4hTCCyA/V41NHC3So+WrYcQXXab2OvCqejUf/vCh+EumkZXrheIMy6EoEx7aTdVdEgeJjgkI1zlO2SPVMYZg/c+EhqldfsZvPTzjGc94xjOe8YxnPOMZz/xfjPy2f5rVZ0aytZm7turWLDaMpJdqptz0aUGhYkKg2Gzfy+O3KsYIo5+99eu0VZ1cz5r1O3Uj6XV6nzxew5ToPpn9mKWKsbmANB86UksAQ8fw4a4+I9UBfCHL85YCmxf1mUWMtLP2FV2YQPuK3resfqbKPiRJf8LNG4D+hHSvoxibqnD3q+Mk2AeLjhnBSgFsHNVnwgwzs9N4VTqxbjIEOdhsneI75ZwyDk7zdW4y7dQ8g5b76ABKqH4omC5gDwBI4EDbmq1Lj+VtgVNUMS0EcAAtCpyybiJLat0QIEov3RCeaqdL5Lbs9WhbM5W2lDStKSRDcUEQ5IYkjavGRWkMiaKKMY4sS/oAxnaSPhx06i+i/hvuGc94xjOe8YxnPPPSmV8Di2ObvTZvPwAAAABJRU5ErkJggg=="
)


def main() -> int:
    result = extract_local_ocr(
        base64.b64decode(_FIXTURE_B64, validate=True),
        content_type="image/png",
        language="hin+eng",
    )
    text = result["text"]
    passed = all(token in text for token in ("किसान", "कार्ड", "Kisan", "Card")) and result["network_used"] is False
    print(json.dumps({
        "status": "pass" if passed else "fail",
        "test": "synthetic_hindi_english_offline_ocr",
        "engine": result["engine"],
        "language": result["language"],
        "average_confidence": result["average_confidence"],
        "expected_tokens_found": {token: token in text for token in ("किसान", "कार्ड", "Kisan", "Card")},
        "network_used": result["network_used"],
        "limitations": "Synthetic fixture only; not representative-document accuracy acceptance.",
    }, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

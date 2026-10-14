"""Black-box smoke checks for a locally running Saathi stack.

Usage:
  python scripts/local_smoke.py --api-only
  python scripts/local_smoke.py --frontend-only
  python scripts/local_smoke.py  # checks both services
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_URL = os.environ.get("SAATHI_API_URL", "http://127.0.0.1:8000").rstrip("/")
FRONTEND_URL = os.environ.get("SAATHI_FRONTEND_URL", "http://127.0.0.1:3000").rstrip("/")


def get_json(path: str) -> dict:
    with urlopen(f"{API_URL}{path}", timeout=5) as response:
        if response.status != 200:
            raise AssertionError(f"{path}: expected HTTP 200, got {response.status}")
        return json.loads(response.read().decode("utf-8"))


def check_api() -> None:
    health = get_json("/health")
    assert health.get("status") == "ok", f"unexpected health response: {health}"
    assert health.get("service") == "saathi-api", f"unexpected service: {health}"

    ready = get_json("/health/ready")
    assert ready.get("status") == "ready", f"API is not ready: {ready}"

    schemes = get_json("/api/v1/schemes")
    assert isinstance(schemes.get("schemes"), list), "scheme catalogue is missing"
    assert schemes["schemes"], "scheme catalogue unexpectedly empty"

    payload = json.dumps(
        {"message": "PM-KISAN scheme ki jankari do", "language": "hi"}
    ).encode("utf-8")
    request = Request(
        f"{API_URL}/api/v1/conversation",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        if response.status != 200:
            raise AssertionError(f"conversation: expected HTTP 200, got {response.status}")
        conversation = json.loads(response.read().decode("utf-8"))
    assert isinstance(conversation.get("reply"), str) and conversation["reply"].strip(), (
        "conversation endpoint returned an empty reply"
    )
    assert conversation.get("demo") is True, "credential-free smoke test must remain in demo mode"
    print("PASS API: health, readiness, scheme catalogue, Hindi conversation")


def check_frontend() -> None:
    with urlopen(f"{FRONTEND_URL}/dashboard", timeout=10) as response:
        body = response.read()
        content_type = response.headers.get("content-type", "")
        assert response.status == 200, f"dashboard returned HTTP {response.status}"
        assert "text/html" in content_type, f"unexpected dashboard content type: {content_type}"
        assert len(body) > 500, "dashboard HTML is unexpectedly small"
    print("PASS frontend: /dashboard responds with rendered HTML")


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--api-only", action="store_true")
    group.add_argument("--frontend-only", action="store_true")
    args = parser.parse_args()

    try:
        if not args.frontend_only:
            check_api()
        if not args.api_only:
            check_frontend()
    except (AssertionError, HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"FAIL local smoke check: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from threading import Lock
from typing import Protocol

import httpx


class WebhookEventStore(Protocol):
    def seen_or_record(self, event_id: str) -> bool: ...


@dataclass
class InMemoryWebhookEventStore:
    _events: set[str]

    def __init__(self) -> None:
        self._events = set()
        self._lock = Lock()

    def seen_or_record(self, event_id: str) -> bool:
        with self._lock:
            if event_id in self._events:
                return True
            self._events.add(event_id)
            return False


def derive_event_id(raw_body: bytes, provider_event_id: str | None = None) -> str:
    if provider_event_id:
        return provider_event_id.strip()[:200]
    return "sha256:" + sha256(raw_body).hexdigest()


async def record_supabase_webhook_event(
    *,
    base_url: str,
    secret_key: str,
    event_id: str,
    event_type: str | None,
    timeout_seconds: float = 3.0,
) -> bool:
    """Atomically claim an event using the table's unique event_id constraint.

    Returns True for a duplicate, False for a newly claimed event. Fails closed
    on network/configuration errors; callers must not acknowledge an event if
    durable idempotency could not be established.
    """
    if not base_url.strip() or not secret_key.strip() or not event_id.strip():
        raise ValueError("durable_webhook_configuration_required")
    headers = {
        "apikey": secret_key,
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    payload = {
        "event_id": event_id[:200],
        "event_type": event_type[:120] if event_type else None,
        "processing_status": "received",
    }
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.post(
            f"{base_url.rstrip('/')}/rest/v1/telephony_webhook_events",
            headers=headers,
            json=payload,
        )
    if response.status_code == 409:
        return True
    if not response.is_success:
        raise RuntimeError(f"durable_webhook_store_http_{response.status_code}")
    return False

from __future__ import annotations

import logging
from uuid import UUID

import httpx

from .config import get_settings

_logger = logging.getLogger("saathi.supabase")


async def record_conversation_metadata(
    *,
    household_id: str | None,
    agent_used: str,
    tools_called: list[str],
    confidence_score: float | None,
    language_code: str,
    correlation_id: str | None,
    response_class: str,
) -> bool:
    """Write privacy-minimised operational metadata to Supabase.

    Raw prompts, transcripts, assistant responses, phone numbers and secrets are
    deliberately excluded. A failed audit write must not take down the core
    assistance flow, but is logged for operators.
    """
    settings = get_settings()
    base_url = (settings.supabase_url or "").rstrip("/")
    secret_key = settings.supabase_secret_key
    if not base_url or not secret_key:
        return False

    valid_household_id: str | None = None
    if household_id:
        try:
            valid_household_id = str(UUID(household_id))
        except (ValueError, TypeError, AttributeError):
            # Demo IDs such as "demo-household" are not persisted as FK values.
            valid_household_id = None

    payload = {
        "household_id": valid_household_id,
        "agent_used": agent_used[:100],
        "tools_called": [item[:100] for item in tools_called[:20]],
        "confidence_score": confidence_score,
        "language_code": language_code[:20] or "hi",
        "correlation_id": correlation_id[:128] if correlation_id else None,
        "response_class": response_class[:40],
    }
    headers = {
        "apikey": secret_key,
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.post(
                f"{base_url}/rest/v1/conversations",
                headers=headers,
                json=payload,
            )
        if response.is_success:
            return True
        _logger.warning("supabase_audit_write_failed status=%s", response.status_code)
    except httpx.HTTPError as exc:
        _logger.warning("supabase_audit_write_failed error_type=%s", type(exc).__name__)
    return False

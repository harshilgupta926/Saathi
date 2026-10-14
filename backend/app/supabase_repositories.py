from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import httpx

from .config import get_settings
from .domain import Consent, ConsentType, Task, TaskStatus


class SupabaseRepositoryError(RuntimeError):
    """A persistence operation failed; callers must not treat it as success."""


class _SupabaseRepository:
    def _configuration(self) -> tuple[str, str, dict[str, str]]:
        settings = get_settings()
        base_url = (settings.supabase_url or "").rstrip("/")
        secret_key = settings.supabase_secret_key or ""
        if not base_url or not secret_key:
            raise SupabaseRepositoryError("supabase_persistence_not_configured")
        return base_url, secret_key, {
            "apikey": secret_key,
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    @staticmethod
    def _uuid(value: str) -> str:
        try:
            return str(UUID(value))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("valid_household_uuid_required") from exc

    async def _request(self, method: str, path: str, payload: dict | None = None) -> list[dict]:
        base_url, _, headers = self._configuration()
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.request(
                    method,
                    f"{base_url}/rest/v1/{path}",
                    headers=headers,
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise SupabaseRepositoryError("supabase_persistence_unavailable") from exc
        if not response.is_success:
            # Avoid including response bodies: they may contain user data.
            raise SupabaseRepositoryError(f"supabase_persistence_http_{response.status_code}")
        if not response.content:
            return []
        try:
            data = response.json()
        except ValueError as exc:
            raise SupabaseRepositoryError("supabase_persistence_invalid_response") from exc
        if not isinstance(data, list):
            raise SupabaseRepositoryError("supabase_persistence_invalid_response")
        return data


class SupabaseConsentRepository(_SupabaseRepository):
    """Server-only consent adapter. No browser key is accepted."""

    _columns = {
        ConsentType.MEMORY: ("memory_consent", "memory_consent_at", "memory_consent_revoked_at"),
        ConsentType.OUTBOUND_CALLS: (
            "outbound_call_consent",
            "outbound_call_consent_at",
            "outbound_call_consent_revoked_at",
        ),
    }

    async def create_household(
        self,
        *,
        preferred_language: str = "hi",
        phone_number: str | None = None,
        dialect_context: dict | None = None,
    ) -> str:
        payload = {
            "preferred_language": preferred_language[:20] or "hi",
            "dialect_context": dialect_context or {},
            "memory_consent": False,
            "outbound_call_consent": False,
        }
        if phone_number:
            payload["phone_number"] = phone_number
        rows = await self._request("POST", "saathi_households", payload)
        if not rows or not rows[0].get("id"):
            raise SupabaseRepositoryError("household_create_failed")
        return str(rows[0]["id"])

    async def get(self, *, household_id: str, consent_type: ConsentType) -> Consent | None:
        if consent_type not in self._columns:
            return None
        household_uuid = self._uuid(household_id)
        granted_column, recorded_column, revoked_column = self._columns[consent_type]
        rows = await self._request(
            "GET",
            f"saathi_households?id=eq.{household_uuid}&select=id,{granted_column},{recorded_column},{revoked_column}",
        )
        if not rows:
            return None
        row = rows[0]
        consent_at_value = row.get(recorded_column)
        revoked_at_value = row.get(revoked_column)
        consent_at = (
            datetime.fromisoformat(str(consent_at_value).replace("Z", "+00:00"))
            if consent_at_value
            else None
        )
        revoked_at = (
            datetime.fromisoformat(str(revoked_at_value).replace("Z", "+00:00"))
            if revoked_at_value
            else None
        )
        granted = bool(row.get(granted_column, False))
        if granted and revoked_at and consent_at and revoked_at >= consent_at:
            granted = False
        effective_time = consent_at if granted else (revoked_at or consent_at)
        if effective_time is None:
            if granted:
                raise SupabaseRepositoryError("consent_timestamp_missing")
            return None
        return Consent(
            household_id=household_uuid,
            consent_type=consent_type,
            granted=granted,
            recorded_at=effective_time,
        )

    async def save(self, consent: Consent) -> Consent:
        if consent.consent_type not in self._columns:
            raise ValueError("unsupported_persisted_consent_type")
        household_uuid = self._uuid(consent.household_id)
        granted_column, recorded_column, revoked_column = self._columns[consent.consent_type]
        payload: dict[str, object] = {
            granted_column: consent.granted,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if consent.granted:
            payload[recorded_column] = consent.recorded_at.isoformat()
            payload[revoked_column] = None
        else:
            payload[revoked_column] = consent.recorded_at.isoformat()
        rows = await self._request(
            "PATCH",
            f"saathi_households?id=eq.{household_uuid}&select=id",
            payload,
        )
        if not rows:
            raise SupabaseRepositoryError("household_not_found")
        return consent


class SupabaseTaskRepository(_SupabaseRepository):
    """Persistent task adapter with household-scoped reads and updates."""

    @staticmethod
    def _to_task(row: dict) -> Task:
        scheduled = row.get("scheduled_callback")
        return Task(
            task_id=str(row["id"]),
            household_id=str(row["household_id"]),
            title=str(row["title"]),
            status=TaskStatus(row["status"]),
            missing_items=list(row.get("missing_requirements") or []),
            scheduled_callback=(
                datetime.fromisoformat(str(scheduled).replace("Z", "+00:00"))
                if scheduled
                else None
            ),
        )

    async def create(self, task: Task) -> Task:
        household_uuid = self._uuid(task.household_id)
        idempotency_key = task.idempotency_key
        payload = {
            "household_id": household_uuid,
            "title": task.title,
            "status": task.status.value,
            "missing_requirements": task.missing_items,
            "scheduled_callback": task.scheduled_callback.isoformat() if task.scheduled_callback else None,
            "idempotency_key": idempotency_key,
        }
        try:
            rows = await self._request("POST", "saathi_pending_tasks", payload)
        except SupabaseRepositoryError as exc:
            if "http_409" not in str(exc):
                raise
            rows = await self._request(
                "GET",
                f"saathi_pending_tasks?idempotency_key=eq.{idempotency_key}&select=id,household_id,title,status,missing_requirements,scheduled_callback",
            )
        if not rows:
            raise SupabaseRepositoryError("task_create_failed")
        return self._to_task(rows[0])

    async def list_open(self, *, household_id: str) -> list[Task]:
        household_uuid = self._uuid(household_id)
        rows = await self._request(
            "GET",
            f"saathi_pending_tasks?household_id=eq.{household_uuid}&status=eq.pending&select=id,household_id,title,status,missing_requirements,scheduled_callback&order=created_at.desc",
        )
        return [self._to_task(row) for row in rows]

    async def set_status(self, *, household_id: str, task_id: str, status: TaskStatus) -> Task:
        household_uuid = self._uuid(household_id)
        task_uuid = self._uuid(task_id)
        rows = await self._request(
            "PATCH",
            f"saathi_pending_tasks?id=eq.{task_uuid}&household_id=eq.{household_uuid}&select=id,household_id,title,status,missing_requirements,scheduled_callback",
            {"status": status.value, "updated_at": datetime.now(timezone.utc).isoformat()},
        )
        if not rows:
            raise KeyError("task_not_found")
        return self._to_task(rows[0])



class SupabaseCallRepository(_SupabaseRepository):
    """Persist outbound call lifecycle metadata before and after provider placement."""

    async def create(
        self,
        *,
        household_id: str,
        phone_number: str,
        provider: str,
        language: str = "hi",
    ) -> str:
        household_uuid = self._uuid(household_id)
        internal_call_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        rows = await self._request(
            "POST",
            "saathi_calls",
            {
                "call_id": internal_call_id,
                "household_id": household_uuid,
                "phone_number": phone_number[:20],
                "direction": "outbound",
                "status": "connecting",
                "provider": provider[:80],
                "language": language[:20] or "hi",
                "started_at": now,
                "updated_at": now,
            },
        )
        if not rows:
            raise SupabaseRepositoryError("call_record_create_failed")
        return internal_call_id

    async def mark_accepted(self, *, call_id: str, provider_call_id: str) -> None:
        call_uuid = self._uuid(call_id)
        rows = await self._request(
            "PATCH",
            f"saathi_calls?call_id=eq.{call_uuid}&select=call_id",
            {
                "provider_call_id": provider_call_id[:200],
                "status": "connecting",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        if not rows:
            raise SupabaseRepositoryError("call_record_not_found")

    async def mark_failed(self, *, call_id: str) -> None:
        call_uuid = self._uuid(call_id)
        now = datetime.now(timezone.utc).isoformat()
        rows = await self._request(
            "PATCH",
            f"saathi_calls?call_id=eq.{call_uuid}&select=call_id",
            {"status": "failed", "ended_at": now, "updated_at": now},
        )
        if not rows:
            raise SupabaseRepositoryError("call_record_not_found")

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx


@dataclass(frozen=True)
class DocumentJob:
    job_id: str
    status: str


class SarvamDocumentAIProvider:
    """Sarvam Document AI adapter using the current /doc-ai/v1 job lifecycle."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.sarvam.ai",
        timeout_seconds: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {"api-subscription-key": self.api_key}

    @staticmethod
    def _json_object(response: httpx.Response) -> dict[str, Any]:
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("document_ai_invalid_response")
        return body

    @staticmethod
    def _job(body: dict[str, Any]) -> DocumentJob:
        job_id = str(body.get("job_id") or body.get("id") or "").strip()
        if not job_id:
            raise ValueError("document_ai_missing_job_id")
        return DocumentJob(job_id=job_id, status=str(body.get("status") or "pending"))

    async def digitise(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        language: str = "hi-IN",
        output_format: str = "md",
    ) -> DocumentJob:
        if output_format not in {"md", "html", "json"}:
            raise ValueError("output_format must be md, html, or json")
        if not content:
            raise ValueError("document_content_empty")
        files = {"file": (filename, content, content_type)}
        data = {"language": language, "output_format": output_format}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/doc-ai/v1/job/digitise",
                headers=self._headers(),
                files=files,
                data=data,
            )
            response.raise_for_status()
            return self._job(self._json_object(response))

    async def status(self, job_id: str) -> dict[str, Any]:
        if not job_id.strip():
            raise ValueError("document_ai_job_id_required")
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                f"{self.base_url}/doc-ai/v1/job/{quote(job_id, safe=chr(0))}/status",
                headers=self._headers(),
            )
            response.raise_for_status()
            return self._json_object(response)

    async def results(self, job_id: str) -> dict[str, Any]:
        if not job_id.strip():
            raise ValueError("document_ai_job_id_required")
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                f"{self.base_url}/doc-ai/v1/job/{quote(job_id, safe=chr(0))}/results",
                headers=self._headers(),
            )
            response.raise_for_status()
            return self._json_object(response)

    async def extract(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        schema: dict[str, Any],
        language: str = "hi-IN",
        output_format: str = "json",
    ) -> DocumentJob:
        if not content:
            raise ValueError("document_content_empty")
        if output_format not in {"json", "csv", "xlsx"}:
            raise ValueError("extract output_format must be json, csv, or xlsx")
        if schema.get("type") != "object" or not isinstance(schema.get("properties"), dict) or not schema["properties"]:
            raise ValueError("extract schema must be a non-empty object schema")
        files = {"file": (filename, content, content_type)}
        data = {
            "language": language,
            "schema": json.dumps(schema),
            "output_format": output_format,
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/doc-ai/v1/job/extract",
                headers=self._headers(),
                files=files,
                data=data,
            )
            response.raise_for_status()
            return self._job(response.json())

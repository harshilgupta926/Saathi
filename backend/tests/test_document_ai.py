import asyncio

from app import document_ai


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.request = None

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    response = FakeResponse({"job_id": "job-1", "status": "pending"})
    calls = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, *args, **kwargs):
        self.calls.append(("post", args, kwargs))
        return self.response

    async def get(self, *args, **kwargs):
        self.calls.append(("get", args, kwargs))
        return self.response


def test_digitise_uses_current_job_endpoint(monkeypatch):
    FakeClient.calls = []
    monkeypatch.setattr(document_ai.httpx, "AsyncClient", FakeClient)
    provider = document_ai.SarvamDocumentAIProvider("key")
    job = asyncio.run(provider.digitise(
        filename="notice.pdf",
        content=b"pdf",
        content_type="application/pdf",
    ))
    assert job.job_id == "job-1"
    assert FakeClient.calls[0][1][0].endswith("/doc-ai/v1/job/digitise")


def test_status_uses_explicit_status_endpoint(monkeypatch):
    FakeClient.calls = []
    monkeypatch.setattr(document_ai.httpx, "AsyncClient", FakeClient)
    provider = document_ai.SarvamDocumentAIProvider("key")
    asyncio.run(provider.status("job-1"))
    assert FakeClient.calls[0][1][0].endswith("/doc-ai/v1/job/job-1/status")


def test_extract_requires_object_schema(monkeypatch):
    monkeypatch.setattr(document_ai.httpx, "AsyncClient", FakeClient)
    provider = document_ai.SarvamDocumentAIProvider("key")
    try:
        asyncio.run(provider.extract(
            filename="form.pdf",
            content=b"pdf",
            content_type="application/pdf",
            schema={"type": "string"},
        ))
    except ValueError as exc:
        assert "object schema" in str(exc)
    else:
        raise AssertionError("invalid schema should fail before provider call")


def test_job_endpoints_encode_provider_job_id(monkeypatch):
    FakeClient.calls = []
    monkeypatch.setattr(document_ai.httpx, "AsyncClient", FakeClient)
    provider = document_ai.SarvamDocumentAIProvider("key")
    asyncio.run(provider.status("job/with space"))
    assert FakeClient.calls[0][1][0].endswith("/doc-ai/v1/job/job%2Fwith%20space/status")


def test_provider_non_object_json_is_rejected(monkeypatch):
    class ListResponse(FakeResponse):
        def json(self):
            return ["unexpected", "array"]

    class ListClient(FakeClient):
        async def get(self, *args, **kwargs):
            return ListResponse([])

    monkeypatch.setattr(document_ai.httpx, "AsyncClient", ListClient)
    provider = document_ai.SarvamDocumentAIProvider("key")
    try:
        asyncio.run(provider.results("job-1"))
    except ValueError as exc:
        assert str(exc) == "document_ai_invalid_response"
    else:
        raise AssertionError("non-object provider response must fail closed")

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.domain import Task, TaskStatus
from app.main import app


HOUSEHOLD_ID = "22222222-2222-4222-8222-222222222222"
IDENTITY_ID = "11111111-1111-4111-8111-111111111111"
TASK_ID = "33333333-3333-4333-8333-333333333333"


def configure_production(monkeypatch):
    monkeypatch.setenv("SAATHI_HOUSEHOLD_FEATURES_ENABLED", "true")
    monkeypatch.setattr(
        "app.main.settings",
        SimpleNamespace(app_env="production", demo_mode=False, api_auth_token="server-token"),
    )


def headers():
    return {
        "X-Saathi-API-Key": "server-token",
        "X-Saathi-Verified-Identity": IDENTITY_ID,
        "X-Saathi-Verified-Household": HOUSEHOLD_ID,
    }


def test_task_list_requires_verified_household(monkeypatch):
    configure_production(monkeypatch)
    response = TestClient(app).get("/api/v1/household/tasks", headers={"X-Saathi-API-Key": "server-token"})
    assert response.status_code == 401
    assert response.json()["detail"] == "verified_phone_identity_required"


def test_task_create_scopes_household_and_idempotency_to_verified_identity(monkeypatch):
    configure_production(monkeypatch)
    captured = {}

    async def create(self, task):
        captured["task"] = task
        return task.model_copy(update={"task_id": TASK_ID})

    monkeypatch.setattr("app.main.SupabaseTaskRepository.create", create)
    response = TestClient(app).post(
        "/api/v1/household/tasks",
        headers=headers(),
        json={"title": "  Call the agriculture office  ", "missing_items": [" land record ", ""], "idempotency_key": "client-request-1"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "task_id": TASK_ID,
        "title": "Call the agriculture office",
        "status": "pending",
        "missing_items": ["land record"],
        "scheduled_callback": None,
    }
    assert captured["task"].household_id == HOUSEHOLD_ID
    assert captured["task"].status == TaskStatus.PENDING
    assert captured["task"].idempotency_key == f"{HOUSEHOLD_ID}:client-request-1"


def test_task_create_rejects_client_supplied_household_id(monkeypatch):
    configure_production(monkeypatch)
    response = TestClient(app).post(
        "/api/v1/household/tasks",
        headers=headers(),
        json={"title": "Private task", "household_id": "44444444-4444-4444-8444-444444444444"},
    )
    assert response.status_code == 422


def test_task_status_update_is_scoped_to_verified_household(monkeypatch):
    configure_production(monkeypatch)
    captured = {}

    async def set_status(self, *, household_id, task_id, status):
        captured.update(household_id=household_id, task_id=task_id, status=status)
        return Task(
            task_id=task_id,
            household_id=household_id,
            title="Call the agriculture office",
            status=status,
        )

    monkeypatch.setattr("app.main.SupabaseTaskRepository.set_status", set_status)
    response = TestClient(app).post(
        "/api/v1/household/tasks/status",
        headers=headers(),
        json={"task_id": TASK_ID, "status": "completed"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert captured == {"household_id": HOUSEHOLD_ID, "task_id": TASK_ID, "status": TaskStatus.COMPLETED}


def test_task_status_update_returns_not_found_for_other_household(monkeypatch):
    configure_production(monkeypatch)

    async def set_status(self, *, household_id, task_id, status):
        assert household_id == HOUSEHOLD_ID
        raise KeyError("task_not_found")

    monkeypatch.setattr("app.main.SupabaseTaskRepository.set_status", set_status)
    response = TestClient(app).post(
        "/api/v1/household/tasks/status",
        headers=headers(),
        json={"task_id": TASK_ID, "status": "cancelled"},
    )
    assert response.status_code == 404

def test_household_features_are_disabled_without_explicit_flag(monkeypatch):
    configure_production(monkeypatch)
    monkeypatch.delenv("SAATHI_HOUSEHOLD_FEATURES_ENABLED", raising=False)
    response = TestClient(app).get("/api/v1/household/tasks", headers=headers())
    assert response.status_code == 503
    assert response.json()["detail"] == "household_features_disabled"

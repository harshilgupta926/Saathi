from datetime import datetime

from .domain import Consent, ConsentType, Task, TaskStatus
from .repositories import ConsentRepository, ConversationRepository, TaskRepository


class InMemoryConsentRepository(ConsentRepository):
    def __init__(self) -> None:
        self._items: dict[tuple[str, ConsentType], Consent] = {}

    async def get(self, *, household_id: str, consent_type: ConsentType) -> Consent | None:
        return self._items.get((household_id, consent_type))

    async def save(self, consent: Consent) -> Consent:
        self._items[(consent.household_id, consent.consent_type)] = consent
        return consent


class InMemoryTaskRepository(TaskRepository):
    def __init__(self) -> None:
        self._items: dict[str, Task] = {}

    async def create(self, task: Task) -> Task:
        task_id = task.task_id or f"task-{len(self._items) + 1}"
        created = task.model_copy(update={"task_id": task_id})
        self._items[task_id] = created
        return created

    async def list_open(self, *, household_id: str) -> list[Task]:
        return [
            task
            for task in self._items.values()
            if task.household_id == household_id and task.status == TaskStatus.PENDING
        ]

    async def set_status(self, *, household_id: str, task_id: str, status: TaskStatus) -> Task:
        task = self._items.get(task_id)
        if task is None or task.household_id != household_id:
            raise KeyError("task_not_found")
        updated = task.model_copy(update={"status": status})
        self._items[task_id] = updated
        return updated


class InMemoryConversationRepository(ConversationRepository):
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def append(
        self,
        *,
        household_id: str,
        role: str,
        message: str,
        language: str,
        created_at: datetime,
    ) -> str:
        message_id = f"message-{len(self.messages) + 1}"
        self.messages.append(
            {
                "id": message_id,
                "household_id": household_id,
                "role": role,
                "message": message,
                "language": language,
                "created_at": created_at,
            }
        )
        return message_id

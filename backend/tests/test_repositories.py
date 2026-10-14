import asyncio
from datetime import datetime, timezone

from app.domain import Consent, ConsentType, Task, TaskStatus
from app.memory_repositories import (
    InMemoryConsentRepository,
    InMemoryConversationRepository,
    InMemoryTaskRepository,
)


def test_consent_repository_is_keyed_by_household_and_type():
    async def run():
        repo = InMemoryConsentRepository()
        consent = Consent(
            household_id="h1",
            consent_type=ConsentType.MEMORY,
            granted=True,
            recorded_at=datetime.now(timezone.utc),
        )
        await repo.save(consent)

        assert await repo.get(household_id="h1", consent_type=ConsentType.MEMORY) == consent
        assert await repo.get(household_id="h2", consent_type=ConsentType.MEMORY) is None

    asyncio.run(run())


def test_task_repository_isolates_households():
    async def run():
        repo = InMemoryTaskRepository()
        await repo.create(Task(household_id="h1", title="Income certificate"))
        await repo.create(Task(household_id="h2", title="Identity proof"))

        tasks = await repo.list_open(household_id="h1")
        assert [task.title for task in tasks] == ["Income certificate"]

    asyncio.run(run())


def test_task_status_update_rejects_cross_household_access():
    async def run():
        repo = InMemoryTaskRepository()
        await repo.create(Task(household_id="h1", title="Call back"))

        try:
            await repo.set_status(
                household_id="h2",
                task_id="task-1",
                status=TaskStatus.COMPLETED,
            )
        except KeyError as exc:
            assert str(exc) == "'task_not_found'"
        else:
            raise AssertionError("cross-household update was accepted")

    asyncio.run(run())


def test_conversation_repository_keeps_language_and_timestamp():
    async def run():
        repo = InMemoryConversationRepository()
        timestamp = datetime.now(timezone.utc)

        message_id = await repo.append(
            household_id="h1",
            role="user",
            message="Namaste",
            language="hi",
            created_at=timestamp,
        )

        assert message_id == "message-1"
        assert repo.messages[0]["language"] == "hi"
        assert repo.messages[0]["created_at"] == timestamp

    asyncio.run(run())


def test_task_creation_is_idempotent_for_the_same_task():
    async def run():
        repo = InMemoryTaskRepository()
        task = Task(household_id="h1", title="Call back")
        first = await repo.create(task)
        second = await repo.create(task)
        assert first.task_id == second.task_id
        assert len(await repo.list_open(household_id="h1")) == 1

    asyncio.run(run())

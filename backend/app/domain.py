from datetime import datetime
from enum import StrEnum
from uuid import uuid4
from pydantic import BaseModel, Field

class ConsentType(StrEnum):
    MEMORY = "memory"
    OUTBOUND_CALLS = "outbound_calls"
    DOCUMENT_PROCESSING = "document_processing"
    RECORDING = "recording"

class TaskStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"

class Consent(BaseModel):
    household_id: str
    consent_type: ConsentType
    granted: bool
    recorded_at: datetime

class Task(BaseModel):
    task_id: str | None = None
    idempotency_key: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=200)
    household_id: str
    title: str = Field(min_length=1, max_length=300)
    status: TaskStatus = TaskStatus.PENDING
    missing_items: list[str] = Field(default_factory=list)
    scheduled_callback: datetime | None = None

from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field

Intent = Literal["scheme", "farming", "document", "task", "general", "human"]
EscalationReason = Literal["low_confidence", "explicit_human_request", "provider_failure", "safety_boundary"]


class LocationContext(BaseModel):
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    label: str | None = Field(default=None, max_length=120)


class ConversationRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    household_id: str | None = Field(default=None, min_length=1, max_length=120)
    language: str = Field(default="hi", min_length=2, max_length=20)
    location: LocationContext | None = None


class SourceResponse(BaseModel):
    name: str
    url: str
    retrieved_at: str | None = None
    freshness_note: str | None = None
    freshness_status: str | None = None


class ConversationResponse(BaseModel):
    status: Literal["needs_input", "ok", "error"]
    reply: str
    intent: Intent | None = None
    task_created: bool = False
    source: SourceResponse | None = None
    sources: list[SourceResponse] = Field(default_factory=list)
    demo: bool = False
    correlation_id: str | None = None
    escalated: bool = False
    escalation_reason: EscalationReason | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    tool_name: str | None = None
    latency_ms: float | None = Field(default=None, ge=0.0)


class ConsentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: Literal["memory", "outbound_calls"]
    granted: bool


class HouseholdTaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=300)
    missing_items: list[str] = Field(default_factory=list, max_length=20)
    idempotency_key: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=160)


class HouseholdTaskStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=36, max_length=36)
    status: Literal["completed", "cancelled"]


class HouseholdMemoryWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_type: str = Field(min_length=1, max_length=80)
    key_name: str = Field(min_length=1, max_length=120)
    value_text: str = Field(min_length=1, max_length=2000)


class HouseholdMemoryDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str = Field(min_length=36, max_length=36)


class AgentRequest(ConversationRequest):
    pass


class VoiceTurnResponse(BaseModel):
    status: Literal["ok", "error"]
    transcript: str | None = None
    reply: str | None = None
    intent: Intent | None = None
    audio_base64: str | None = None
    audio_mime_type: str | None = None
    source: SourceResponse | None = None
    sources: list[SourceResponse] = Field(default_factory=list)
    demo: bool = False
    correlation_id: str | None = None
    escalated: bool = False
    escalation_reason: EscalationReason | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    tool_name: str | None = None
    latency_ms: float | None = Field(default=None, ge=0.0)


class CallRequest(BaseModel):
    to: str = Field(min_length=8, max_length=32)
    callback_url: str | None = Field(default=None, min_length=8, max_length=500)
    consent: bool = False
    household_id: str | None = Field(default=None, min_length=1, max_length=80)
    language: str = Field(default="hi", min_length=2, max_length=20)
    realtime_voice_ai: bool = False

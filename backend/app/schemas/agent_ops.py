from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AgentStepOut(BaseModel):
    id: UUID
    node_name: str
    status: str
    latency_ms: int
    error: str | None
    started_at: datetime

    model_config = {"from_attributes": True}


class AgentRunOut(BaseModel):
    id: UUID
    conversation_id: UUID
    query: str
    status: str
    error: str | None
    latency_ms: int | None
    started_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class AgentRunDetailOut(AgentRunOut):
    steps: list[AgentStepOut]


class AgentOpsStats(BaseModel):
    window_minutes: int
    total_runs: int
    error_count: int
    error_rate: float
    avg_latency_ms: float | None
    p95_latency_ms: float | None

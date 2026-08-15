from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationOut(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    citations: list[dict]
    feedback: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut]


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class FeedbackRequest(BaseModel):
    feedback: str | None = Field(default=None, pattern="^(up|down)$")

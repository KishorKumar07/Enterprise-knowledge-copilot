from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DriveFolderOut(BaseModel):
    id: str
    name: str
    parent_id: str | None


class SelectedFolderIn(BaseModel):
    id: str
    name: str
    path: str


class SelectFoldersRequest(BaseModel):
    folders: list[SelectedFolderIn]


class SlackChannelOut(BaseModel):
    id: str
    name: str
    is_private: bool


class SelectedChannelIn(BaseModel):
    id: str
    name: str


class SelectChannelsRequest(BaseModel):
    channels: list[SelectedChannelIn]


class KnowledgeSourceOut(BaseModel):
    id: UUID
    external_id: str
    name: str
    path: str | None
    document_count: int
    last_synced_at: datetime | None

    model_config = {"from_attributes": True}


class ConnectionStatusOut(BaseModel):
    connected: bool
    configured: bool
    status: str | None = None
    account_label: str | None = None
    last_error: str | None = None
    sources: list[KnowledgeSourceOut] = []
    active_sync_job_id: UUID | None = None


class SyncJobOut(BaseModel):
    id: UUID
    provider: str
    status: str
    total_items: int
    processed_items: int
    progress_percent: int
    current_item: str | None
    error: str | None
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}

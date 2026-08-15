import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KnowledgeSource(Base):
    """A single selected Drive folder or Slack channel to index."""

    __tablename__ = "knowledge_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("connections.id", ondelete="CASCADE"), nullable=False
    )

    provider: Mapped[str] = mapped_column(String(32), nullable=False)  # "google_drive" | "slack"
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # "folder" | "channel"
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Drive folder ID / Slack channel ID
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str | None] = mapped_column(String(1024), nullable=True)  # display path, e.g. "Engineering/Specs"

    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    document_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

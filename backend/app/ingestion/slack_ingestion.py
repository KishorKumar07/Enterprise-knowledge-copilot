import hashlib
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.connectors import slack
from app.core.database import async_session_factory
from app.core.encryption import decrypt_value
from app.models.connection import Connection
from app.models.document import Document
from app.models.knowledge_source import KnowledgeSource
from app.models.sync_job import SyncJob
from app.services.chunk_indexing import index_document

logger = logging.getLogger("ekc.ingestion.slack")


def _format_transcript(channel_name: str, messages: list[slack.SlackMessage], names: dict[str, str]) -> str:
    lines = [f"#{channel_name}"]
    for m in messages:
        speaker = names.get(m.user or "", m.user or "unknown")
        lines.append(f"{speaker}: {m.text}")
    return "\n".join(lines)


async def run_slack_sync(organization_id: UUID, connection_id: UUID, sync_job_id: UUID) -> None:
    async with async_session_factory() as db:
        job = await db.get(SyncJob, sync_job_id)
        if job is None:
            return

        try:
            connection = await db.get(Connection, connection_id)
            if connection is None or connection.status != "connected":
                raise slack.SlackError("Slack is not connected.")

            access_token = decrypt_value(connection.encrypted_access_token)

            sources_result = await db.execute(
                select(KnowledgeSource).where(
                    KnowledgeSource.organization_id == organization_id,
                    KnowledgeSource.connection_id == connection_id,
                    KnowledgeSource.provider == "slack",
                    KnowledgeSource.enabled.is_(True),
                )
            )
            sources = list(sources_result.scalars().all())

            job.status = "running"
            await db.commit()

            user_name_cache: dict[str, str] = {}
            all_threads: list[tuple[KnowledgeSource, str, list[slack.SlackMessage]]] = []

            for source in sources:
                top_level = await slack.fetch_channel_history(access_token, source.external_id)
                for msg in top_level:
                    if msg.thread_ts and msg.thread_ts == msg.ts:
                        replies = await slack.fetch_thread_replies(access_token, source.external_id, msg.ts)
                        thread_messages = replies if replies else [msg]
                    else:
                        thread_messages = [msg]
                    all_threads.append((source, msg.ts, thread_messages))

            job.total_items = len(all_threads)
            await db.commit()

            for source, parent_ts, messages in all_threads:
                job.current_item = f"#{source.name}"
                await db.commit()

                try:
                    for m in messages:
                        if m.user and m.user not in user_name_cache:
                            user_name_cache[m.user] = await slack.get_user_display_name(access_token, m.user)

                    text = _format_transcript(source.name, messages, user_name_cache)
                    checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
                    timestamp = datetime.fromtimestamp(float(parent_ts), tz=timezone.utc)

                    existing = await db.execute(
                        select(Document).where(
                            Document.source_id == source.id,
                            Document.external_id == parent_ts,
                        )
                    )
                    doc = existing.scalar_one_or_none()
                    content_changed = False

                    title = f"#{source.name} — {timestamp.strftime('%b %d, %Y')}"

                    if doc is None:
                        doc = Document(
                            organization_id=organization_id,
                            source_id=source.id,
                            external_id=parent_ts,
                            title=title,
                            content=text,
                            checksum=checksum,
                            doc_metadata={
                                "provider": "slack",
                                "channel_name": source.name,
                                "channel_id": source.external_id,
                                "thread_ts": parent_ts,
                                "message_count": len(messages),
                                "timestamp": timestamp.isoformat(),
                            },
                        )
                        db.add(doc)
                        content_changed = True
                    elif doc.checksum != checksum:
                        doc.content = text
                        doc.checksum = checksum
                        doc.title = title
                        content_changed = True

                    if content_changed:
                        await db.flush()
                        await index_document(db, doc)
                except Exception:
                    logger.exception("Failed to ingest Slack thread %s in %s", parent_ts, source.name)

                job.processed_items += 1
                await db.commit()

            for source in sources:
                count_result = await db.execute(select(Document).where(Document.source_id == source.id))
                source.document_count = len(count_result.scalars().all())
                source.last_synced_at = datetime.now(timezone.utc)

            job.status = "success" if job.processed_items == job.total_items else "partial"
            job.completed_at = datetime.now(timezone.utc)
            job.current_item = None
            await db.commit()

        except slack.SlackError as exc:
            job.status = "failed"
            job.error = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception:
            logger.exception("Slack sync job %s failed", sync_job_id)
            job.status = "failed"
            job.error = "Sync failed unexpectedly. Please try again."
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

import hashlib
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.connectors import google_drive
from app.core.database import async_session_factory
from app.ingestion.parsers import extract_text
from app.models.document import Document
from app.models.knowledge_source import KnowledgeSource
from app.models.sync_job import SyncJob
from app.services.chunk_indexing import index_document
from app.services.connection_tokens import ConnectionUnavailableError, get_valid_google_access_token

logger = logging.getLogger("ekc.ingestion.google_drive")


async def run_google_drive_sync(organization_id: UUID, connection_id: UUID, sync_job_id: UUID) -> None:
    async with async_session_factory() as db:
        job = await db.get(SyncJob, sync_job_id)
        if job is None:
            return

        try:
            from app.models.connection import Connection

            connection = await db.get(Connection, connection_id)
            if connection is None:
                raise ConnectionUnavailableError("Google Drive connection not found.")

            sources_result = await db.execute(
                select(KnowledgeSource).where(
                    KnowledgeSource.organization_id == organization_id,
                    KnowledgeSource.connection_id == connection_id,
                    KnowledgeSource.provider == "google_drive",
                    KnowledgeSource.enabled.is_(True),
                )
            )
            sources = list(sources_result.scalars().all())

            job.status = "running"
            await db.commit()

            access_token = await get_valid_google_access_token(db, connection)

            all_files: list[tuple[KnowledgeSource, google_drive.DriveFile]] = []
            for source in sources:
                files = await google_drive.list_files_in_folder(access_token, source.external_id)
                for f in files:
                    if google_drive.is_ingestible_mime_type(f.mime_type):
                        all_files.append((source, f))

            job.total_items = len(all_files)
            await db.commit()

            processed_per_source: dict[UUID, int] = {}

            for source, file in all_files:
                job.current_item = file.name
                await db.commit()

                try:
                    content = await google_drive.fetch_file_content(access_token, file)
                    if content is not None:
                        raw_bytes, effective_mime = content
                        text = extract_text(effective_mime, raw_bytes)
                        checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()

                        existing = await db.execute(
                            select(Document).where(
                                Document.source_id == source.id,
                                Document.external_id == file.id,
                            )
                        )
                        doc = existing.scalar_one_or_none()
                        content_changed = False

                        if doc is None:
                            doc = Document(
                                organization_id=organization_id,
                                source_id=source.id,
                                external_id=file.id,
                                title=file.name,
                                content=text,
                                checksum=checksum,
                                doc_metadata={
                                    "mime_type": file.mime_type,
                                    "modified_time": file.modified_time,
                                    "source_url": file.web_view_link,
                                    "folder_path": source.path,
                                    "provider": "google_drive",
                                },
                            )
                            db.add(doc)
                            content_changed = True
                        elif doc.checksum != checksum:
                            doc.content = text
                            doc.checksum = checksum
                            doc.title = file.name
                            doc.doc_metadata = {
                                **doc.doc_metadata,
                                "modified_time": file.modified_time,
                            }
                            content_changed = True

                        if content_changed:
                            await db.flush()
                            await index_document(db, doc)

                        processed_per_source[source.id] = processed_per_source.get(source.id, 0) + 1
                except Exception:
                    logger.exception("Failed to ingest Drive file %s", file.id)

                job.processed_items += 1
                await db.commit()

            for source in sources:
                count_result = await db.execute(
                    select(Document).where(Document.source_id == source.id)
                )
                source.document_count = len(count_result.scalars().all())
                source.last_synced_at = datetime.now(timezone.utc)

            job.status = "success" if job.processed_items == job.total_items else "partial"
            job.completed_at = datetime.now(timezone.utc)
            job.current_item = None
            await db.commit()

        except ConnectionUnavailableError as exc:
            job.status = "failed"
            job.error = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Google Drive sync job %s failed", sync_job_id)
            job.status = "failed"
            job.error = "Sync failed unexpectedly. Please try again."
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

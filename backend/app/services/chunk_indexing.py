from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.rag.chunking import chunk_text
from app.rag.embeddings import embed_documents


async def index_document(db: AsyncSession, document: Document) -> int:
    """(Re)chunk and (re)embed a document, replacing any chunks it already has.

    Returns the number of chunks written. Safe to call repeatedly — e.g. when
    a re-sync finds the same file with updated content.
    """
    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))

    base_metadata = {
        "document_title": document.title,
        **{k: v for k, v in document.doc_metadata.items() if k in ("provider", "source_url", "folder_path", "channel_name")},
    }
    chunks = chunk_text(document.content, base_metadata=base_metadata)
    if not chunks:
        return 0

    embeddings = await embed_documents([c.content for c in chunks])

    for chunk, embedding in zip(chunks, embeddings):
        db.add(
            DocumentChunk(
                document_id=document.id,
                organization_id=document.organization_id,
                chunk_index=chunk.index,
                content=chunk.content,
                embedding=embedding,
                chunk_metadata=chunk.metadata,
            )
        )

    return len(chunks)


async def reindex_all_pending(db: AsyncSession, organization_id) -> int:
    """Index any documents in the org that have no chunks yet."""
    result = await db.execute(
        select(Document).where(Document.organization_id == organization_id)
    )
    documents = result.scalars().all()

    total = 0
    for document in documents:
        existing = await db.execute(
            select(DocumentChunk.id).where(DocumentChunk.document_id == document.id).limit(1)
        )
        if existing.scalar_one_or_none() is None:
            total += await index_document(db, document)

    await db.commit()
    return total

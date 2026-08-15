"""Hybrid retrieval: vector search + keyword search, fused, then reranked.

    query
      -> vector search (pgvector cosine distance)      \
      -> keyword search (Postgres full-text ts_rank)     >  reciprocal rank fusion -> rerank -> top N
      -> metadata filtering (organization_id, provider)  /

Contextual compression (trimming the reranked chunks down to only the
sentences an LLM judges relevant) happens one layer up, in the Phase 5
agent graph — it needs an LLM call, which this module deliberately does
not depend on so it stays fully testable offline.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.rag.embeddings import embed_query
from app.rag.reranker import rerank

VECTOR_CANDIDATES = 25
KEYWORD_CANDIDATES = 25
FUSED_CANDIDATES = 20
RRF_K = 60


@dataclass
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    content: str
    metadata: dict
    score: float


async def _vector_search(
    db: AsyncSession, organization_id: UUID, query_embedding: list[float], provider: str | None
) -> list[UUID]:
    stmt = select(DocumentChunk.id).where(DocumentChunk.organization_id == organization_id)
    if provider:
        stmt = stmt.join(Document, Document.id == DocumentChunk.document_id).where(
            Document.doc_metadata["provider"].astext == provider
        )
    stmt = stmt.order_by(DocumentChunk.embedding.cosine_distance(query_embedding)).limit(VECTOR_CANDIDATES)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _keyword_search(
    db: AsyncSession, organization_id: UUID, query: str, provider: str | None
) -> list[UUID]:
    sql = """
        SELECT dc.id
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE dc.organization_id = :org_id
          AND to_tsvector('english', dc.content) @@ plainto_tsquery('english', :query)
          AND (CAST(:provider AS text) IS NULL OR d.doc_metadata->>'provider' = :provider)
        ORDER BY ts_rank(to_tsvector('english', dc.content), plainto_tsquery('english', :query)) DESC
        LIMIT :limit
    """
    result = await db.execute(
        text(sql),
        {"org_id": str(organization_id), "query": query, "provider": provider, "limit": KEYWORD_CANDIDATES},
    )
    return [row[0] for row in result.all()]


def _reciprocal_rank_fusion(ranked_lists: list[list[UUID]]) -> list[UUID]:
    scores: dict[UUID, float] = {}
    for ranked in ranked_lists:
        for rank, chunk_id in enumerate(ranked):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)
    return [cid for cid, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)]


async def hybrid_search(
    db: AsyncSession,
    organization_id: UUID,
    query: str,
    top_n: int = 6,
    provider: str | None = None,
) -> list[RetrievedChunk]:
    """Run hybrid retrieval + reranking for a single (already understood) query."""
    query_embedding = await embed_query(query)

    vector_ids, keyword_ids = (
        await _vector_search(db, organization_id, query_embedding, provider),
        await _keyword_search(db, organization_id, query, provider),
    )

    fused_ids = _reciprocal_rank_fusion([vector_ids, keyword_ids])[:FUSED_CANDIDATES]
    if not fused_ids:
        return []

    result = await db.execute(
        select(DocumentChunk, Document.title)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.id.in_(fused_ids))
    )
    rows = {chunk.id: (chunk, title) for chunk, title in result.all()}
    ordered = [rows[cid] for cid in fused_ids if cid in rows]

    scores = await rerank(query, [chunk.content for chunk, _ in ordered])

    candidates = [
        RetrievedChunk(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_title=title,
            content=chunk.content,
            metadata=chunk.chunk_metadata,
            score=score,
        )
        for (chunk, title), score in zip(ordered, scores)
    ]
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:top_n]

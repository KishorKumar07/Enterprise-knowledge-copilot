"""Local cross-encoder reranker — no external API needed."""

import asyncio
from functools import lru_cache

from sentence_transformers import CrossEncoder

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache
def _model() -> CrossEncoder:
    return CrossEncoder(MODEL_NAME)


def _rerank_sync(query: str, documents: list[str]) -> list[float]:
    pairs = [(query, doc) for doc in documents]
    scores = _model().predict(pairs)
    return [float(s) for s in scores]


async def rerank(query: str, documents: list[str]) -> list[float]:
    """Return a relevance score per document, same order as input."""
    if not documents:
        return []
    return await asyncio.to_thread(_rerank_sync, query, documents)

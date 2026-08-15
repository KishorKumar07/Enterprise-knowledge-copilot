"""Local embedding model.

Runs entirely on-device via sentence-transformers so Phase 4 (embeddings,
pgvector, hybrid retrieval, reranking) needs no external API key.
"""

import asyncio
from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"


@lru_cache
def _model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def _embed_sync(texts: list[str], is_query: bool) -> list[list[float]]:
    model = _model()
    # bge models are trained with an instruction prefix on the query side only.
    inputs = [f"Represent this question for retrieval: {t}" for t in texts] if is_query else texts
    vectors = model.encode(inputs, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vectors]


async def embed_documents(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return await asyncio.to_thread(_embed_sync, texts, False)


async def embed_query(text: str) -> list[float]:
    vectors = await asyncio.to_thread(_embed_sync, [text], True)
    return vectors[0]

"""Retrieval Agent — query rewriting/expansion, hybrid retrieval, and
context selection. Delegates the actual vector+keyword+rerank work to
app.rag.retrieval, which is deliberately LLM-free so it stays unit-testable
without an API key; this node adds the LLM-driven query expansion on top.
"""

from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import AgentState
from app.rag.retrieval import RetrievedChunk, hybrid_search
from app.services import llm

MAX_CONTEXT_CHUNKS = 8

REWRITE_SYSTEM_PROMPT = """You expand a user's question into up to 2 alternate
search phrasings that might match different wording in company documents or
Slack messages. Reply with each alternate phrasing on its own line, nothing
else — no numbering, no explanation. If the question is already clear and
specific, reply with just the original question unchanged."""


async def _expand_query(query: str) -> list[str]:
    if not llm.is_configured():
        return [query]
    try:
        raw = await llm.complete(REWRITE_SYSTEM_PROMPT, query, max_tokens=120)
        variants = [line.strip() for line in raw.splitlines() if line.strip()]
        return [query, *variants[:2]] if variants else [query]
    except Exception:
        return [query]


async def retrieval_node(state: AgentState, config: RunnableConfig) -> dict:
    if not state.get("needs_retrieval", True):
        return {"search_queries": [], "retrieved_chunks": []}

    db: AsyncSession = config["configurable"]["db"]
    organization_id = state["organization_id"]

    queries = await _expand_query(state["query"])

    best_by_id: dict[str, RetrievedChunk] = {}
    for q in queries:
        for chunk in await hybrid_search(db, organization_id, q, top_n=MAX_CONTEXT_CHUNKS):
            existing = best_by_id.get(str(chunk.chunk_id))
            if existing is None or chunk.score > existing.score:
                best_by_id[str(chunk.chunk_id)] = chunk

    merged = sorted(best_by_id.values(), key=lambda c: c.score, reverse=True)[:MAX_CONTEXT_CHUNKS]

    return {"search_queries": queries, "retrieved_chunks": merged}

from typing import TypedDict
from uuid import UUID

from app.rag.retrieval import RetrievedChunk


class ChatTurn(TypedDict):
    role: str
    content: str


class AgentState(TypedDict, total=False):
    organization_id: UUID
    query: str
    history: list[ChatTurn]

    needs_retrieval: bool
    supervisor_reasoning: str

    search_queries: list[str]
    retrieved_chunks: list[RetrievedChunk]

    research_notes: str

    answer: str
    citations: list[dict]

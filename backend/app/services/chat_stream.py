import json
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import build_graph
from app.agents.state import ChatTurn
from app.models.message import Message

logger = logging.getLogger("ekc.chat")

MAX_HISTORY_TURNS = 10

_graph = build_graph()


def _sse(event: dict) -> bytes:
    return f"data: {json.dumps(event)}\n\n".encode("utf-8")


async def stream_agent_turn(
    db: AsyncSession,
    request: Request,
    organization_id: UUID,
    conversation_id: UUID,
    query: str,
    history: list[ChatTurn],
) -> AsyncIterator[bytes]:
    """Run the agent graph for one turn, streaming SSE events and persisting
    the assistant's reply once generation finishes (or the client disconnects)."""

    initial_state = {
        "organization_id": organization_id,
        "query": query,
        "history": history[-MAX_HISTORY_TURNS:],
    }
    config = {"configurable": {"db": db}}

    final_state: dict = {}

    try:
        async for mode, payload in _graph.astream(initial_state, config=config, stream_mode=["custom", "values"]):
            if await request.is_disconnected():
                break

            if mode == "custom":
                yield _sse(payload)
            elif mode == "values":
                final_state = payload
    except Exception:
        logger.exception("Agent graph failed for conversation %s", conversation_id)
        yield _sse({"type": "error", "text": "Something went wrong generating a response. Please try again."})
        return

    answer = final_state.get("answer", "")
    citations = final_state.get("citations", [])

    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
        citations=citations,
    )
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)

    yield _sse(
        {
            "type": "done",
            "message_id": str(assistant_message.id),
            "citations": citations,
        }
    )

import json
import logging
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import build_graph
from app.agents.state import ChatTurn
from app.core.metrics import agent_run_duration_seconds, agent_run_total
from app.core.tracing import get_tracer
from app.models.agent_run import AgentRun
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

    run = AgentRun(conversation_id=conversation_id, organization_id=organization_id, query=query)
    db.add(run)
    await db.commit()
    await db.refresh(run)

    initial_state = {
        "organization_id": organization_id,
        "query": query,
        "history": history[-MAX_HISTORY_TURNS:],
        "run_id": run.id,
    }
    config = {"configurable": {"db": db}}

    final_state: dict = {}
    started = time.perf_counter()

    async def _finish_run(status: str, error: str | None = None) -> None:
        latency_ms = int((time.perf_counter() - started) * 1000)
        agent_run_duration_seconds.observe(latency_ms / 1000)
        agent_run_total.labels(status=status).inc()
        run.status = status
        run.error = error
        run.latency_ms = latency_ms
        run.finished_at = datetime.now(UTC)
        await db.commit()

    try:
        with get_tracer().start_as_current_span("agent.run") as span:
            span.set_attribute("agent.run_id", str(run.id))
            span.set_attribute("agent.conversation_id", str(conversation_id))
            async for mode, payload in _graph.astream(
                initial_state, config=config, stream_mode=["custom", "values"]
            ):
                if await request.is_disconnected():
                    break

                if mode == "custom":
                    yield _sse(payload)
                elif mode == "values":
                    final_state = payload
    except Exception as exc:
        logger.exception("Agent graph failed for conversation %s", conversation_id)
        await _finish_run("error", str(exc))
        yield _sse({"type": "error", "text": "Something went wrong generating a response. Please try again."})
        return

    # answer_node catches its own LLM failures to stream a friendly message
    # instead of crashing — it signals that via "_error" rather than raising,
    # so the graph completes normally. Reflect that as a failed run, not a
    # successful one.
    run_error = final_state.get("_error")
    await _finish_run("error" if run_error else "completed", run_error)

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

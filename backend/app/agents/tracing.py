"""Wraps each LangGraph node with three layers of agent_ops observability:

- an OpenTelemetry span (visible as a trace waterfall in Phoenix)
- a Prometheus histogram/counter observation (visible in Grafana)
- an AgentStep row (the durable, per-run audit trail in Postgres)

A single decorator drives all three so graph.py stays a plain node list.
"""

import inspect
import logging
import time
from collections.abc import Awaitable, Callable

from langchain_core.runnables import RunnableConfig
from opentelemetry.trace import Status, StatusCode
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import AgentState
from app.core.metrics import agent_node_duration_seconds, agent_node_total
from app.core.tracing import get_tracer
from app.models.agent_run import AgentStep

logger = logging.getLogger("ekc.agents.tracing")

NodeFn = Callable[..., Awaitable[dict]]


async def _persist_step(db: AsyncSession | None, run_id, node_name: str, status: str, latency_ms: int, error: str | None) -> None:
    if db is None or run_id is None:
        return
    try:
        db.add(AgentStep(run_id=run_id, node_name=node_name, status=status, latency_ms=latency_ms, error=error))
        await db.commit()
    except Exception:
        logger.warning("Failed to persist agent_steps row for node %s", node_name, exc_info=True)


def traced_node(node_name: str, fn: NodeFn) -> NodeFn:
    accepted_params = set(inspect.signature(fn).parameters)
    tracer = get_tracer()

    async def wrapper(state: AgentState, config: RunnableConfig, writer=None) -> dict:
        kwargs = {}
        if "config" in accepted_params:
            kwargs["config"] = config
        if "writer" in accepted_params:
            kwargs["writer"] = writer

        db: AsyncSession | None = (config or {}).get("configurable", {}).get("db")
        run_id = state.get("run_id")

        started = time.perf_counter()
        status = "success"
        error: str | None = None

        with tracer.start_as_current_span(f"agent.{node_name}") as span:
            span.set_attribute("agent.node", node_name)
            try:
                result = await fn(state, **kwargs)
                # Some nodes (answer_agent) catch their own LLM-call failures
                # so they can still stream a friendly message instead of
                # crashing the response — they signal that via "_error" on
                # the returned dict rather than raising. Without this check
                # that kind of failure would be recorded as a success.
                soft_error = result.get("_error") if isinstance(result, dict) else None
                if soft_error:
                    status = "error"
                    error = str(soft_error)
                    span.set_status(Status(StatusCode.ERROR))
                return result
            except Exception as exc:
                status = "error"
                error = str(exc)
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                raise
            finally:
                latency_ms = int((time.perf_counter() - started) * 1000)
                span.set_attribute("agent.status", status)
                span.set_attribute("agent.latency_ms", latency_ms)
                agent_node_duration_seconds.labels(node=node_name).observe(latency_ms / 1000)
                agent_node_total.labels(node=node_name, status=status).inc()
                await _persist_step(db, run_id, node_name, status, latency_ms, error)

    wrapper.__name__ = getattr(fn, "__name__", node_name)
    return wrapper

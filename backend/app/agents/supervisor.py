"""Supervisor Agent — decides whether the question needs knowledge-base
retrieval at all, so trivial exchanges ("thanks!", "hi") don't trigger
unnecessary retrieval/rerank work.
"""

from app.agents.state import AgentState
from app.services import llm

SYSTEM_PROMPT = """You are the routing supervisor for an enterprise knowledge assistant.
Decide whether answering the user's latest message requires searching the
company's connected Google Drive and Slack knowledge base.

Answer with exactly one word: RETRIEVE or DIRECT.

Use RETRIEVE for any question that could be answered from company documents,
policies, past discussions, or decisions — including implicit follow-ups.
Use DIRECT only for greetings, thanks, small talk, or questions about how to
use this assistant."""


async def supervisor_node(state: AgentState) -> dict:
    query = state["query"]

    if not llm.is_configured():
        # No LLM configured — default to retrieving so the pipeline still
        # exercises hybrid search; the answer step will surface the real error.
        return {"needs_retrieval": True, "supervisor_reasoning": "LLM not configured; defaulting to retrieval."}

    decision = await llm.complete(SYSTEM_PROMPT, query, max_tokens=8)
    needs_retrieval = "DIRECT" not in decision.upper()

    return {
        "needs_retrieval": needs_retrieval,
        "supervisor_reasoning": decision.strip(),
    }

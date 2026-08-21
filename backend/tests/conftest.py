import pytest

from app.services import llm


@pytest.fixture(autouse=True)
def _reset_llm_clients():
    """app/services/llm.py caches its async httpx-backed clients at module
    scope, reused across requests within one long-lived event loop (how the
    real app runs). pytest-asyncio gives each test its own event loop, so a
    client cached from a previous test would be bound to an already-closed
    loop. Forcing a fresh client per test keeps each one on its own loop.
    """
    llm._gemini_client = None
    llm._groq_client = None
    yield
    llm._gemini_client = None
    llm._groq_client = None

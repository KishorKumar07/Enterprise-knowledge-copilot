"""RAG quality gate: runs the real research_agent + answer_agent nodes
against fixed golden contexts (see golden_dataset.py) and grades the output
with an LLM judge (see judge.py). Skips automatically if no LLM is
configured, and needs no database — only the generation stage is exercised,
not retrieval, so this runs anywhere GEMINI_API_KEY/GROQ_API_KEY is set.
"""

from uuid import uuid4

import pytest

from app.agents.answer_agent import answer_node
from app.agents.research_agent import research_node
from app.rag.retrieval import RetrievedChunk
from app.services import llm
from tests.eval.golden_dataset import GOLDEN_CASES
from tests.eval.judge import score_faithfulness, score_relevancy

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not llm.is_configured(), reason="Requires GEMINI_API_KEY or GROQ_API_KEY"),
]

FAITHFULNESS_THRESHOLD = 0.7
RELEVANCY_THRESHOLD = 0.7


def _null_writer(_event: dict) -> None:
    pass


async def _generate(question: str, context: str) -> str:
    chunks = (
        [
            RetrievedChunk(
                chunk_id=uuid4(),
                document_id=uuid4(),
                document_title="eval-fixture",
                content=context,
                metadata={},
                score=1.0,
            )
        ]
        if context
        else []
    )
    state = {"query": question, "history": [], "retrieved_chunks": chunks}
    state = {**state, **await research_node(state)}
    result = await answer_node(state, _null_writer)
    return result["answer"]


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=lambda c: c.id)
async def test_answer_is_faithful_and_relevant(case):
    answer = await _generate(case.question, case.context)

    faithfulness = await score_faithfulness(context=case.context, answer=answer)
    relevancy = await score_relevancy(question=case.question, answer=answer)

    assert faithfulness >= FAITHFULNESS_THRESHOLD, f"Low faithfulness ({faithfulness}) for {case.id!r}: {answer}"
    assert relevancy >= RELEVANCY_THRESHOLD, f"Low relevancy ({relevancy}) for {case.id!r}: {answer}"

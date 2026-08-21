"""LLM-as-judge scoring, in the same spirit as RAGAS's faithfulness/answer
relevancy metrics: prompt the configured LLM (Gemini/Groq, via
app/services/llm.py) to grade an answer and parse a 0.0-1.0 score back out.

Hand-rolled instead of using the RAGAS library — see the comment in
requirements.txt: RAGAS's current release forces a langgraph/langchain
upgrade that breaks this project's pinned agent runtime.
"""

import re

from app.services import llm

_SCORE_RE = re.compile(r"([01](?:\.\d+)?)")

FAITHFULNESS_PROMPT = """You are grading whether an AI answer is faithful to its source context —
i.e. every claim in the answer is directly supported by the context, with no
fabricated or contradicted facts. An answer that correctly admits it doesn't
have enough information should score 1.0, even if the context is empty.

Score from 0.0 (fabricated/contradicted) to 1.0 (fully supported).
Respond with ONLY the number, nothing else.

Context:
{context}

Answer:
{answer}"""

RELEVANCY_PROMPT = """You are grading whether an AI answer actually addresses the question asked
— regardless of whether the answer is correct or complete. A response that
honestly declines to answer because it lacks evidence still counts as
relevant, since it directly engages with the question.

Score from 0.0 (off-topic) to 1.0 (directly addresses the question).
Respond with ONLY the number, nothing else.

Question:
{question}

Answer:
{answer}"""


def _parse_score(raw: str) -> float:
    match = _SCORE_RE.search(raw)
    if not match:
        raise ValueError(f"Judge did not return a parseable score: {raw!r}")
    return max(0.0, min(1.0, float(match.group(1))))


async def score_faithfulness(context: str, answer: str) -> float:
    prompt = FAITHFULNESS_PROMPT.format(context=context or "(no context was provided)", answer=answer)
    raw = await llm.complete(system="You are a strict, precise grading assistant.", prompt=prompt, max_tokens=10)
    return _parse_score(raw)


async def score_relevancy(question: str, answer: str) -> float:
    prompt = RELEVANCY_PROMPT.format(question=question, answer=answer)
    raw = await llm.complete(system="You are a strict, precise grading assistant.", prompt=prompt, max_tokens=10)
    return _parse_score(raw)

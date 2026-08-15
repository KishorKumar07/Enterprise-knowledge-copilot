"""LLM abstraction with automatic provider fallback.

Primary: Gemini (google-genai SDK).
Fallback: Groq (OpenAI-compatible SDK) — used when Gemini is unconfigured,
or when a Gemini call fails before it has produced any output.

This is the single place in the app that talks to a model provider. Agents,
the chat API, and everything else only ever call is_configured() / complete()
/ stream_completion() — swapping or adding a provider means changing only
this file.
"""

import logging
from collections.abc import AsyncIterator

import httpx
from google import genai
from google.genai import types as genai_types
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.ssl_bundle import get_ca_bundle_path

settings = get_settings()
logger = logging.getLogger("ekc.llm")

_gemini_client: genai.Client | None = None
_groq_client: AsyncOpenAI | None = None


def _new_async_http_client() -> httpx.AsyncClient:
    # See app/core/ssl_bundle.py — avoids a truststore/asyncio recursion bug
    # on Windows by using a plain SSLContext built from a static CA bundle.
    return httpx.AsyncClient(verify=get_ca_bundle_path())


class LLMNotConfiguredError(Exception):
    pass


def _gemini_configured() -> bool:
    return bool(settings.gemini_api_key)


def _groq_configured() -> bool:
    return bool(settings.groq_api_key)


def is_configured() -> bool:
    return _gemini_configured() or _groq_configured()


def _get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=genai_types.HttpOptions(httpx_async_client=_new_async_http_client()),
        )
    return _gemini_client


def _get_groq_client() -> AsyncOpenAI:
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            http_client=_new_async_http_client(),
        )
    return _groq_client


def _to_gemini_contents(messages: list[dict[str, str]]) -> list[dict]:
    # Gemini uses "model" where everyone else uses "assistant".
    return [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
        for m in messages
    ]


# ---- non-streaming "utility" calls (routing, query rewriting, synthesis) ----


async def complete(system: str, prompt: str, max_tokens: int = 1024) -> str:
    if _gemini_configured():
        try:
            client = _get_gemini_client()
            response = await client.aio.models.generate_content(
                model=settings.gemini_utility_model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system, max_output_tokens=max_tokens
                ),
            )
            return response.text or ""
        except Exception:
            logger.warning("Gemini completion failed, falling back to Groq", exc_info=True)

    if _groq_configured():
        client = _get_groq_client()
        response = await client.chat.completions.create(
            model=settings.groq_utility_model,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""

    raise LLMNotConfiguredError(
        "AI generation is not configured yet. Add a GEMINI_API_KEY or GROQ_API_KEY to enable chat."
    )


# ---- streaming call for the final grounded answer ----


async def _stream_gemini(system: str, messages: list[dict[str, str]], max_tokens: int) -> AsyncIterator[str]:
    client = _get_gemini_client()
    stream = await client.aio.models.generate_content_stream(
        model=settings.gemini_model,
        contents=_to_gemini_contents(messages),
        config=genai_types.GenerateContentConfig(system_instruction=system, max_output_tokens=max_tokens),
    )
    async for chunk in stream:
        if chunk.text:
            yield chunk.text


async def _stream_groq(system: str, messages: list[dict[str, str]], max_tokens: int) -> AsyncIterator[str]:
    client = _get_groq_client()
    stream = await client.chat.completions.create(
        model=settings.groq_model,
        max_tokens=max_tokens,
        messages=[{"role": "system", "content": system}, *messages],
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


async def stream_completion(
    system: str, messages: list[dict[str, str]], max_tokens: int = 2048
) -> AsyncIterator[str]:
    if not is_configured():
        raise LLMNotConfiguredError(
            "AI generation is not configured yet. Add a GEMINI_API_KEY or GROQ_API_KEY to enable chat."
        )

    if _gemini_configured():
        yielded_any = False
        try:
            async for token in _stream_gemini(system, messages, max_tokens):
                yielded_any = True
                yield token
            return
        except Exception:
            if yielded_any:
                # Already streamed partial output to the client — surfacing a
                # provider switch mid-answer would be more confusing than useful.
                raise
            logger.warning("Gemini streaming failed before any output, falling back to Groq", exc_info=True)

    if _groq_configured():
        async for token in _stream_groq(system, messages, max_tokens):
            yield token
        return

    raise LLMNotConfiguredError("Gemini failed and no Groq fallback is configured.")

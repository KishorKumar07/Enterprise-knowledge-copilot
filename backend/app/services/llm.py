"""LLM abstraction with automatic provider fallback.

Providers: Groq (OpenAI-compatible SDK) and Gemini (google-genai SDK). Which one
is tried first is the LLM_PRIMARY setting; the other is the fallback, used when
the primary is unconfigured or a call to it fails before producing any output.

This is the single place in the app that talks to a model provider. Agents,
the chat API, and everything else only ever call is_configured() / complete()
/ stream_completion() — swapping or adding a provider means changing only
this file.
"""

import logging
import time
from collections.abc import AsyncIterator

import httpx
from google import genai
from google.genai import types as genai_types
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.metrics import llm_call_total, llm_fallback_total, llm_latency_seconds
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


def _provider_order() -> list[str]:
    """Configured providers, the LLM_PRIMARY one first. Empty if none is configured."""
    available = [name for name, ok in (("gemini", _gemini_configured()), ("groq", _groq_configured())) if ok]
    primary = (settings.llm_primary or "").strip().lower()
    if primary in available:
        return [primary] + [name for name in available if name != primary]
    return available


def _note_failure(kind: str, provider: str, providers: list[str], index: int) -> None:
    llm_call_total.labels(provider, kind, "error").inc()
    if index + 1 < len(providers):
        nxt = providers[index + 1]
        llm_fallback_total.labels(provider, nxt).inc()
        logger.warning("%s %s failed, falling back to %s", provider.title(), kind, nxt.title(), exc_info=True)
    else:
        logger.error("%s %s failed and there is no fallback left", provider.title(), kind, exc_info=True)


def _get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=genai_types.HttpOptions(
                httpx_async_client=_new_async_http_client(),
                # Gemini sometimes returns 503 "high demand". The SDK's default is
                # to retry with backoff for a long time, which stalled answers for
                # ~130s before the Groq fallback ever got a chance. Fail fast instead:
                # a 20s ceiling and no retry (a healthy first token takes ~3s), then
                # the caller falls back to Groq.
                timeout=20_000,
                retry_options=genai_types.HttpRetryOptions(attempts=1),
            ),
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


async def _complete_gemini(system: str, prompt: str, max_tokens: int) -> str:
    client = _get_gemini_client()
    response = await client.aio.models.generate_content(
        model=settings.gemini_utility_model,
        contents=prompt,
        config=genai_types.GenerateContentConfig(system_instruction=system, max_output_tokens=max_tokens),
    )
    return response.text or ""


async def _complete_groq(system: str, prompt: str, max_tokens: int) -> str:
    client = _get_groq_client()
    response = await client.chat.completions.create(
        model=settings.groq_utility_model,
        max_tokens=max_tokens,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


async def complete(system: str, prompt: str, max_tokens: int = 1024) -> str:
    providers = _provider_order()
    if not providers:
        raise LLMNotConfiguredError(
            "AI generation is not configured yet. Add a GEMINI_API_KEY or GROQ_API_KEY to enable chat."
        )

    runners = {"gemini": _complete_gemini, "groq": _complete_groq}
    last_error: Exception | None = None
    for index, provider in enumerate(providers):
        started = time.perf_counter()
        try:
            text = await runners[provider](system, prompt, max_tokens)
        except Exception as exc:  # noqa: BLE001 - any provider failure means "try the next one"
            last_error = exc
            _note_failure("complete", provider, providers, index)
            continue
        llm_latency_seconds.labels(provider, "complete").observe(time.perf_counter() - started)
        llm_call_total.labels(provider, "complete", "success").inc()
        return text

    assert last_error is not None
    raise last_error


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
    providers = _provider_order()
    if not providers:
        raise LLMNotConfiguredError(
            "AI generation is not configured yet. Add a GEMINI_API_KEY or GROQ_API_KEY to enable chat."
        )

    streamers = {"gemini": _stream_gemini, "groq": _stream_groq}
    last_error: Exception | None = None
    for index, provider in enumerate(providers):
        started = time.perf_counter()
        yielded_any = False
        try:
            async for token in streamers[provider](system, messages, max_tokens):
                if not yielded_any:
                    llm_latency_seconds.labels(provider, "stream").observe(time.perf_counter() - started)
                yielded_any = True
                yield token
        except Exception as exc:  # noqa: BLE001
            if yielded_any:
                # Already streamed partial output to the client - surfacing a
                # provider switch mid-answer would be more confusing than useful.
                llm_call_total.labels(provider, "stream", "error").inc()
                raise
            last_error = exc
            _note_failure("stream", provider, providers, index)
            continue
        llm_call_total.labels(provider, "stream", "success").inc()
        return

    assert last_error is not None
    raise last_error

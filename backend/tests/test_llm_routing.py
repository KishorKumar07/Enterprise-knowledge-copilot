"""Provider routing in app/services/llm.py, tested with fake providers.

No network, no API keys: the real _complete_*/_stream_* functions are replaced,
so these pin down the ORDER and FALLBACK behaviour only.
"""

import pytest
from prometheus_client import REGISTRY

from app.services import llm


def _count(name: str, **labels) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


@pytest.fixture
def providers(monkeypatch):
    """Both providers configured, Groq primary (the default)."""
    monkeypatch.setattr(llm, "_gemini_configured", lambda: True)
    monkeypatch.setattr(llm, "_groq_configured", lambda: True)
    monkeypatch.setattr(llm.settings, "llm_primary", "groq")


# ---- order ----

def test_primary_is_tried_first(providers, monkeypatch):
    assert llm._provider_order() == ["groq", "gemini"]
    monkeypatch.setattr(llm.settings, "llm_primary", "gemini")
    assert llm._provider_order() == ["gemini", "groq"]


def test_primary_setting_is_case_and_space_insensitive(providers, monkeypatch):
    monkeypatch.setattr(llm.settings, "llm_primary", "  Gemini ")
    assert llm._provider_order() == ["gemini", "groq"]


def test_unconfigured_primary_is_skipped(monkeypatch):
    monkeypatch.setattr(llm, "_gemini_configured", lambda: True)
    monkeypatch.setattr(llm, "_groq_configured", lambda: False)
    monkeypatch.setattr(llm.settings, "llm_primary", "groq")
    assert llm._provider_order() == ["gemini"]


def test_unknown_primary_falls_back_to_default_order(providers, monkeypatch):
    monkeypatch.setattr(llm.settings, "llm_primary", "nonsense")
    assert sorted(llm._provider_order()) == ["gemini", "groq"]


# ---- complete() ----

async def test_complete_uses_primary_and_does_not_touch_fallback(providers, monkeypatch):
    calls = []

    async def groq(*a):
        calls.append("groq")
        return "from groq"

    async def gemini(*a):
        calls.append("gemini")
        return "from gemini"

    monkeypatch.setattr(llm, "_complete_groq", groq)
    monkeypatch.setattr(llm, "_complete_gemini", gemini)

    assert await llm.complete("sys", "hi") == "from groq"
    assert calls == ["groq"]


async def test_complete_falls_back_and_counts_it(providers, monkeypatch):
    async def groq(*a):
        raise TimeoutError("groq down")

    async def gemini(*a):
        return "from gemini"

    monkeypatch.setattr(llm, "_complete_groq", groq)
    monkeypatch.setattr(llm, "_complete_gemini", gemini)
    before = _count("llm_fallback_total", from_provider="groq", to_provider="gemini")
    errors_before = _count("llm_call_total", provider="groq", kind="complete", outcome="error")

    assert await llm.complete("sys", "hi") == "from gemini"

    assert _count("llm_fallback_total", from_provider="groq", to_provider="gemini") == before + 1
    assert _count("llm_call_total", provider="groq", kind="complete", outcome="error") == errors_before + 1


async def test_complete_raises_the_real_error_when_everything_fails(providers, monkeypatch):
    async def boom(*a):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(llm, "_complete_groq", boom)
    monkeypatch.setattr(llm, "_complete_gemini", boom)

    with pytest.raises(RuntimeError, match="provider exploded"):
        await llm.complete("sys", "hi")


async def test_complete_with_nothing_configured_says_so(monkeypatch):
    monkeypatch.setattr(llm, "_gemini_configured", lambda: False)
    monkeypatch.setattr(llm, "_groq_configured", lambda: False)

    with pytest.raises(llm.LLMNotConfiguredError):
        await llm.complete("sys", "hi")


# ---- stream_completion() ----

def _fake_stream(tokens, fail_after=None):
    async def gen(*a):
        for i, token in enumerate(tokens):
            if fail_after is not None and i == fail_after:
                raise ConnectionError("stream broke")
            yield token
        if fail_after is not None and fail_after >= len(tokens):
            raise ConnectionError("stream broke")

    return gen


async def _collect(**kwargs):
    return [t async for t in llm.stream_completion("sys", [{"role": "user", "content": "hi"}], **kwargs)]


async def test_stream_uses_primary_only_when_healthy(providers, monkeypatch):
    monkeypatch.setattr(llm, "_stream_groq", _fake_stream(["a", "b"]))
    monkeypatch.setattr(llm, "_stream_gemini", _fake_stream(["WRONG"]))

    assert await _collect() == ["a", "b"]


async def test_stream_falls_back_when_primary_fails_before_any_output(providers, monkeypatch):
    monkeypatch.setattr(llm, "_stream_groq", _fake_stream(["never"], fail_after=0))
    monkeypatch.setattr(llm, "_stream_gemini", _fake_stream(["x", "y"]))
    before = _count("llm_fallback_total", from_provider="groq", to_provider="gemini")

    assert await _collect() == ["x", "y"]
    assert _count("llm_fallback_total", from_provider="groq", to_provider="gemini") == before + 1


async def test_stream_does_not_switch_provider_mid_answer(providers, monkeypatch):
    """Once tokens reached the user, a failure must surface, not splice in a second model."""
    monkeypatch.setattr(llm, "_stream_groq", _fake_stream(["a", "b", "c"], fail_after=2))
    monkeypatch.setattr(llm, "_stream_gemini", _fake_stream(["SHOULD-NOT-APPEAR"]))

    received = []
    with pytest.raises(ConnectionError):
        async for token in llm.stream_completion("sys", [{"role": "user", "content": "hi"}]):
            received.append(token)

    assert received == ["a", "b"]


async def test_stream_raises_when_all_providers_fail(providers, monkeypatch):
    monkeypatch.setattr(llm, "_stream_groq", _fake_stream([], fail_after=0))
    monkeypatch.setattr(llm, "_stream_gemini", _fake_stream([], fail_after=0))

    with pytest.raises(ConnectionError):
        await _collect()

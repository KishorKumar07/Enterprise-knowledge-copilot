"""Deterministic unit tests: no network, no API keys, no database.

These are what CI gates on. The LLM-judge suite in tests/eval is deliberately
kept out of the per-push gate — it is nondeterministic and spends API quota.
"""

import uuid

import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.core import encryption
from app.core.config import get_settings
from app.rag.chunking import MIN_CHUNK_CHARS, TARGET_CHUNK_CHARS, chunk_text
from app.rag.retrieval import _reciprocal_rank_fusion


# ---- chunking ----

def test_chunk_text_empty_input_gives_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_chunk_text_records_section_heading_and_base_metadata():
    body = "Employees accrue leave monthly from their first day. " * 4
    chunks = chunk_text(f"# Leave Policy\n\n{body}", {"provider": "google_drive"})

    assert chunks
    assert chunks[0].metadata["provider"] == "google_drive"
    assert chunks[0].metadata["section"] == "Leave Policy"


def test_chunk_text_indexes_are_sequential_and_chunks_stay_bounded():
    paragraph = "The deployment pipeline runs lint, tests and a health check. " * 6
    text = "\n\n".join(f"## Section {i}\n\n{paragraph}" for i in range(8))

    chunks = chunk_text(text)

    assert len(chunks) > 1
    assert [c.index for c in chunks] == list(range(len(chunks)))
    # A chunk may exceed the target slightly (overlap, merged tail), never wildly.
    assert all(len(c.content) <= TARGET_CHUNK_CHARS * 2 for c in chunks)


def test_chunk_text_never_loses_content():
    text = "# Title\n\n" + "\n\n".join(f"Fact number {i} is recorded here for the test. " * 3 for i in range(12))
    joined = " ".join(c.content for c in chunk_text(text))

    for i in range(12):
        assert f"Fact number {i} " in joined


def test_chunk_text_merges_tiny_trailing_piece_into_previous_chunk():
    text = ("A reasonably long first paragraph about authentication tokens. " * 4) + "\n\nTiny."
    chunks = chunk_text(text)

    assert all(len(c.content) >= MIN_CHUNK_CHARS for c in chunks)
    assert "Tiny." in chunks[-1].content


# ---- reciprocal rank fusion (hybrid search) ----

def test_rrf_prefers_items_ranked_by_both_retrievers():
    a, b, c = (uuid.uuid4() for _ in range(3))
    vector_hits = [a, b]
    keyword_hits = [c, a]

    fused = _reciprocal_rank_fusion([vector_hits, keyword_hits])

    assert fused[0] == a  # present in both lists, so it outranks either single-list item
    assert set(fused) == {a, b, c}


def test_rrf_handles_empty_lists():
    assert _reciprocal_rank_fusion([]) == []
    assert _reciprocal_rank_fusion([[], []]) == []


def test_rrf_is_stable_for_a_single_list():
    ids = [uuid.uuid4() for _ in range(4)]
    assert _reciprocal_rank_fusion([ids]) == ids


# ---- OAuth token encryption ----

@pytest.fixture
def fernet_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", key)
    get_settings.cache_clear()
    encryption._fernet.cache_clear()
    yield key
    get_settings.cache_clear()
    encryption._fernet.cache_clear()


def test_encrypt_decrypt_round_trip(fernet_key):
    token = "ya29.a0-secret-oauth-access-token"
    ciphertext = encryption.encrypt_value(token)

    assert ciphertext != token
    assert token not in ciphertext
    assert encryption.decrypt_value(ciphertext) == token


def test_decrypt_rejects_data_encrypted_under_another_key(fernet_key):
    foreign = Fernet(Fernet.generate_key()).encrypt(b"x").decode()

    with pytest.raises(InvalidToken):
        encryption.decrypt_value(foreign)


def test_encrypt_requires_a_configured_key(monkeypatch):
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", "")
    get_settings.cache_clear()
    encryption._fernet.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="CREDENTIAL_ENCRYPTION_KEY"):
            encryption.encrypt_value("anything")
    finally:
        get_settings.cache_clear()
        encryption._fernet.cache_clear()

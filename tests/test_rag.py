"""Tests for rag.py. Search and the LLM are replaced with fakes (monkeypatch), so these
check only the glue: numbering, prompt layout, and the empty-index shortcut."""

import pytest

from docpilot import config, rag

HITS = [
    {"text": "Use Query(default=None).", "source": "fastapi/query.md", "score": 0.81},
    {"text": "Path params are required.", "source": "fastapi/path.md", "score": 0.64},
]


def test_build_context_numbers_chunks_from_one() -> None:
    context = rag.build_context(HITS)

    assert context == (
        "[1] (source: fastapi/query.md)\nUse Query(default=None).\n\n"
        "[2] (source: fastapi/path.md)\nPath params are required."
    )


def test_ask_sends_context_and_question_to_the_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    sent = {}

    def fake_chat(client, system: str, user: str) -> str:
        sent["system"], sent["user"] = system, user
        return "Make it optional with Query(default=None) [1]."

    monkeypatch.setattr(rag, "embed_query", lambda question: [0.0] * config.EMBEDDING_DIM)
    monkeypatch.setattr(rag, "search", lambda client, name, vector, top_k: HITS[:top_k])
    monkeypatch.setattr(rag, "chat", fake_chat)

    result = rag.ask("How do I make a query parameter optional?", None, None)

    assert result["answer"] == "Make it optional with Query(default=None) [1]."
    assert result["sources"] == HITS
    assert sent["system"] == rag.SYSTEM_PROMPT
    assert sent["user"].startswith("Context:\n[1] (source: fastapi/query.md)")
    assert sent["user"].endswith("Question: How do I make a query parameter optional?")


def test_empty_index_returns_not_found_without_llm_call(monkeypatch: pytest.MonkeyPatch) -> None:
    def chat_must_not_run(*args, **kwargs):
        raise AssertionError("the LLM was called with no context")

    monkeypatch.setattr(rag, "embed_query", lambda question: [0.0] * config.EMBEDDING_DIM)
    monkeypatch.setattr(rag, "search", lambda client, name, vector, top_k: [])
    monkeypatch.setattr(rag, "chat", chat_must_not_run)

    result = rag.ask("anything", None, None)

    assert result == {"answer": config.NOT_FOUND_PHRASE, "sources": []}


def test_system_prompt_contains_the_exact_not_found_phrase() -> None:
    # Evals count abstentions by this phrase, so prompt and config must never drift apart.
    assert config.NOT_FOUND_PHRASE in rag.SYSTEM_PROMPT

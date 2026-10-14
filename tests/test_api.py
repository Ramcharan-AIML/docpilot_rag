"""Tests for the mini API. ask() is replaced by a fake, so no model, no Qdrant, no API key."""

import pytest
from fastapi.testclient import TestClient

from docpilot import api


def fake_ask(question, qdrant_client, llm_client):
    """Stands in for rag.ask: returns the same shape, instantly."""
    hit = {"source": "fastapi/demo.md", "chunk_number": 3, "score": 0.81, "text": "secret"}
    return {"answer": f"fake answer to: {question}", "sources": [hit], "timings_ms": {}}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api, "ask", fake_ask)
    # TestClient(app) WITHOUT `with` does not run the lifespan, so nothing real opens.
    # The endpoint still reads app.state, so give it placeholders.
    monkeypatch.setattr(api.app.state, "qdrant", None, raising=False)
    monkeypatch.setattr(api.app.state, "llm", None, raising=False)
    return TestClient(api.app)


def test_valid_question_returns_answer_and_sources(client):
    response = client.post("/ask", json={"question": "How do I make it optional?"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "fake answer to: How do I make it optional?"
    assert body["sources"] == [{"source": "fastapi/demo.md", "chunk_number": 3, "score": 0.81}]
    assert "text" not in body["sources"][0]  # chunk text is not sent to the client


def test_empty_question_is_rejected(client):
    assert client.post("/ask", json={"question": ""}).status_code == 422


def test_too_long_question_is_rejected(client):
    long_question = "a" * 3000  # over MAX_QUESTION_CHARS (2000)
    assert client.post("/ask", json={"question": long_question}).status_code == 422


def test_missing_field_is_rejected(client):
    assert client.post("/ask", json={"text": "wrong field name"}).status_code == 422

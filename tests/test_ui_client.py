"""Tests for the UI's API client and formatting. No Streamlit, no real API: requests is faked."""

import pytest
import requests

from ui import api_client
from ui.api_client import ApiError, source_rows, status_note, timing_rows


def test_timing_rows_follow_the_pipeline_order() -> None:
    timings = {"total": 2700.0, "llm": 1591.04, "input_guard": 0.01, "rerank": 993.0}
    assert timing_rows(timings) == [
        {"Stage": "Input guard", "ms": 0.0},
        {"Stage": "Rerank", "ms": 993.0},
        {"Stage": "LLM answer", "ms": 1591.0},
        {"Stage": "Total", "ms": 2700.0},
    ]


def test_unknown_stage_goes_last() -> None:
    rows = timing_rows({"new_stage": 1.0, "total": 2.0})
    assert [row["Stage"] for row in rows] == ["Total", "new_stage"]


def test_sources_are_numbered_like_citations() -> None:
    sources = [
        {"source": "fastapi/query.md", "chunk_number": 3, "score": 0.9},
        {"source": "uploads/notes.pdf", "chunk_number": 0, "score": 0.7},
    ]
    assert source_rows(sources) == [
        {"Cite": "[1]", "Document": "fastapi/query.md", "Chunk": 3},
        {"Cite": "[2]", "Document": "uploads/notes.pdf", "Chunk": 0},
    ]


def test_status_notes() -> None:
    assert status_note("ok") == ""
    assert "input guard" in status_note("blocked_input")
    assert "do not contain" in status_note("not_found")


class FakeResponse:
    def __init__(self, status: int, body):
        self.status_code, self._body = status, body
        self.ok = status < 400

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


def test_api_error_detail_is_shown(monkeypatch) -> None:
    monkeypatch.setattr(
        requests, "request", lambda *a, **k: FakeResponse(400, {"detail": "Only PDF files."})
    )
    with pytest.raises(ApiError, match="Only PDF files."):
        api_client.upload("x.exe", b"MZ")


def test_api_error_without_json_body(monkeypatch) -> None:
    monkeypatch.setattr(
        requests, "request", lambda *a, **k: FakeResponse(500, ValueError("not json"))
    )
    with pytest.raises(ApiError, match="API error 500"):
        api_client.ask("q", "main")


def test_api_down_gives_a_helpful_message(monkeypatch) -> None:
    def refuse(*args, **kwargs):
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(requests, "request", refuse)
    with pytest.raises(ApiError, match="Is uvicorn running"):
        api_client.list_uploads()
    assert api_client.is_api_up() is False


def test_ask_sends_question_and_library(monkeypatch) -> None:
    sent = {}

    def fake_request(method, url, timeout, **kwargs):
        sent.update(method=method, url=url, json=kwargs["json"])
        return FakeResponse(200, {"answer": "a [1]"})

    monkeypatch.setattr(requests, "request", fake_request)
    assert api_client.ask("How?", "uploads", base="http://api:8000") == {"answer": "a [1]"}
    assert sent == {
        "method": "POST",
        "url": "http://api:8000/ask",
        "json": {"question": "How?", "library": "uploads"},
    }

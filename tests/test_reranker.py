"""Tests for retrieval/reranker.py and evals/timing.py.

A fake reranker replaces the real 1.1 GB model, so these run in a moment (also in CI).
The real model is checked by the eval run itself.
"""

import pytest

from docpilot.retrieval import reranker
from evals.timing import StageTimes


class FakeCrossEncoder:
    """Scores a pair by how many question words appear in the chunk."""

    def predict(self, pairs):
        return [sum(word in text for word in question.split()) for question, text in pairs]


@pytest.fixture(autouse=True)
def fake_model(monkeypatch):
    monkeypatch.setattr(reranker, "get_reranker", lambda: FakeCrossEncoder())


def test_best_scored_chunk_moves_to_the_top():
    hits = [{"text": "nothing here"}, {"text": "docker volume"}, {"text": "docker"}]
    result = reranker.rerank("docker volume", hits, keep=3)
    assert [hit["text"] for hit in result] == ["docker volume", "docker", "nothing here"]
    assert [hit["search_rank"] for hit in result] == [2, 3, 1]  # where each one came from


def test_keeps_only_the_best_and_leaves_the_input_alone():
    hits = [{"text": "a"}, {"text": "docker"}]
    result = reranker.rerank("docker", hits, keep=1)
    assert [hit["text"] for hit in result] == ["docker"]
    assert "rerank_score" not in hits[0]  # the caller's dicts were copied, not changed


def test_ties_keep_the_search_order():
    hits = [{"text": "first"}, {"text": "second"}]
    assert [h["text"] for h in reranker.rerank("x", hits, keep=2)] == ["first", "second"]


def test_no_hits_no_model_call():
    assert reranker.rerank("anything", [], keep=5) == []


def test_stage_times_report_p50_and_p95():
    times = StageTimes()
    for _ in range(3):
        with times.measure("rerank"):
            pass
    summary = times.summary()
    assert list(summary) == ["rerank"]
    assert summary["rerank"]["n"] == 3
    assert summary["rerank"]["p50"] <= summary["rerank"]["p95"]

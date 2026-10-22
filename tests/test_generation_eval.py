"""Tests for evals/judge_prompts.py and retrieval/pipeline.py (no LLM, no models)."""

import pytest

from docpilot.retrieval import pipeline
from docpilot.retrieval.pipeline import DENSE_ONLY, RetrievalSettings, retrieve
from evals.judge_prompts import JUDGE_PROMPT, parse_judge

GOOD = (
    '{"claims": [{"claim": "a", "supported": true}, {"claim": "b", "supported": false}],'
    ' "correctness": "Partly", "correctness_reason": "misses x", "relevancy": 4}'
)


def test_parse_judge_scores_faithfulness_and_correctness():
    result = parse_judge("<think>hmm {not json}</think>\n" + GOOD)
    assert result["faithfulness"] == 0.5
    assert result["unsupported_claims"] == ["b"]
    assert result["correctness"] == "partly" and result["correctness_score"] == 0.5
    assert result["relevancy"] == 4


@pytest.mark.parametrize(
    "reply",
    [
        "no json here",
        '{"claims": [], "correctness": "maybe", "relevancy": 3}',
        GOOD.replace("4}", "9}"),
    ],
)
def test_parse_judge_rejects_broken_replies(reply):
    with pytest.raises(ValueError):
        parse_judge(reply)


def test_judge_prompt_formats_without_brace_errors():
    text = JUDGE_PROMPT.format(context="c", question="q", reference="r", answer="a")
    assert '{"claims"' in text


@pytest.fixture
def fakes(monkeypatch):
    calls = {}
    monkeypatch.setattr(pipeline, "embed_query", lambda q: [0.1])
    monkeypatch.setattr(pipeline, "embed_sparse_query", lambda q: {"indices": [1], "values": [1.0]})

    def fake_hits(n):
        return [{"text": f"t{i}", "source": "a.md", "chunk_number": i} for i in range(n)]

    def fake_hybrid(client, name, dense, sparse, top_k, candidates, rrf_k):
        calls["hybrid_top_k"] = top_k
        return fake_hits(top_k)

    def fake_dense(client, name, vector, top_k):
        calls["dense_top_k"] = top_k
        return fake_hits(top_k)

    def fake_rerank(question, hits, keep, name):
        calls["rerank_in"] = len(hits)
        return list(reversed(hits))[:keep]

    monkeypatch.setattr(pipeline, "search_hybrid", fake_hybrid)
    monkeypatch.setattr(pipeline, "search", fake_dense)
    monkeypatch.setattr(pipeline, "rerank", fake_rerank)
    return calls


def test_best_settings_search_20_rerank_and_keep_top_k(fakes):
    timings = {}
    hits = retrieve("q", client=None, settings=RetrievalSettings(top_k=4), timings=timings)
    assert fakes == {"hybrid_top_k": 20, "rerank_in": 20}
    assert [h["chunk_number"] for h in hits] == [19, 18, 17, 16]  # the reranker's order
    assert set(timings) == {"embed_query", "search", "rerank"}


def test_dense_only_is_the_old_app(fakes):
    hits = retrieve("q", client=None, settings=DENSE_ONLY)
    assert fakes == {"dense_top_k": DENSE_ONLY.top_k}
    assert len(hits) == DENSE_ONLY.top_k

"""Tests for retrieval/query_transforms.py, evals/transform_cache.py and multi_search.

A fake LLM returns fixed text, so no API key and no network are needed.
"""

from pathlib import Path

import pytest

from docpilot.ingestion.chunkers.base import Chunk
from docpilot.retrieval.hybrid import multi_search
from docpilot.retrieval.query_transforms import clean_lines, search_texts, transform
from docpilot.store.qdrant_store import add_chunks, create_fresh_collection, get_client
from evals.transform_cache import TransformCache


def fake_llm(reply: str):
    calls = []

    def ask(system: str, user: str) -> str:
        calls.append(user)
        return reply

    return ask, calls


def test_clean_lines_drops_numbers_bullets_and_blank_lines():
    assert clean_lines('1. first\n\n- second\n* "third"\n2) fourth') == [
        "first",
        "second",
        "third",
        "fourth",
    ]


def test_multi_keeps_at_most_three_rewrites():
    ask, calls = fake_llm("a\nb\nc\nd")
    assert transform("multi", "q?", ask) == ["a", "b", "c"]
    assert "q?" in calls[0]  # the question is inside the prompt


def test_hyde_is_one_passage_embedded_like_a_chunk():
    ask, _ = fake_llm("Line one.\nLine two.")
    passage = transform("hyde", "q?", ask)
    assert passage == ["Line one. Line two."]
    assert search_texts("hyde", "q?", passage) == [("q?", False), ("Line one. Line two.", True)]


def test_stepback_keeps_one_line_and_original_is_always_searched():
    ask, _ = fake_llm("What is X?\nextra")
    texts = search_texts("stepback", "How to X?", transform("stepback", "How to X?", ask))
    assert texts == [("How to X?", False), ("What is X?", False)]


def test_decompose_repeat_of_the_question_is_not_searched_twice():
    ask, _ = fake_llm("How to X?")
    assert search_texts("decompose", "How to X?", transform("decompose", "How to X?", ask)) == [
        ("How to X?", False)
    ]


def test_unknown_transform_raises():
    with pytest.raises(ValueError):
        transform("magic", "q?", fake_llm("")[0])


def test_cache_calls_the_llm_once_per_question(tmp_path: Path):
    ask, calls = fake_llm("a\nb")
    cache = TransformCache("multi", ask=ask, folder=tmp_path)
    assert cache.get("q?")["texts"] == ["a", "b"]
    cache.get("q?")
    assert len(calls) == 1 and cache.new_calls == 1
    # A new cache object reads the saved file: no LLM needed at all (ask=None).
    assert TransformCache("multi", folder=tmp_path).get("q?")["texts"] == ["a", "b"]


def test_multi_search_merges_lists_of_several_queries(tmp_path: Path):
    client = get_client(tmp_path / "qdrant")
    try:
        create_fresh_collection(client, "t", dimension=4)
        chunks = [Chunk(text=f"text {i}", source="a.md", chunk_number=i) for i in range(3)]
        vectors = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]]
        sparse = [{"indices": [i + 1], "values": [1.0]} for i in range(3)]
        add_chunks(client, "t", chunks, vectors, sparse)
        # Query 1 points at chunk 0, query 2 at chunk 2; each list has only its 1st.
        queries = [
            ([1.0, 0.0, 0.0, 0.0], {"indices": [1], "values": [1.0]}),
            ([0.0, 0.0, 1.0, 0.0], {"indices": [3], "values": [1.0]}),
        ]
        hits = multi_search(client, "t", queries, top_k=1, candidates=1)
        both = multi_search(client, "t", queries, top_k=3, candidates=1)
    finally:
        client.close()
    assert hits[0]["chunk_number"] == 0  # tie: the original question's list comes first
    assert {hit["chunk_number"] for hit in both} == {0, 2}

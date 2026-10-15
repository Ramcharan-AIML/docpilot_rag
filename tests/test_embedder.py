"""Tests for embedder.py. These load the real model (a few seconds, cached after the first
download), so they check shapes and lengths only, never similarity scores."""

import math

from docpilot import config
from docpilot.embedder import embed_documents, embed_query, get_model


def length(vector: list[float]) -> float:
    return math.sqrt(sum(x * x for x in vector))


def test_documents_give_one_normalised_vector_each() -> None:
    vectors = embed_documents(["first chunk", "second chunk"])

    assert len(vectors) == 2
    for vector in vectors:
        assert len(vector) == config.EMBEDDING_DIM
        assert math.isclose(length(vector), 1.0, abs_tol=1e-5)


def test_query_gives_one_normalised_vector() -> None:
    vector = embed_query("How do I make a query parameter optional?")

    assert len(vector) == config.EMBEDDING_DIM
    assert math.isclose(length(vector), 1.0, abs_tol=1e-5)


def test_empty_list_gives_empty_list() -> None:
    assert embed_documents([]) == []


def test_model_is_loaded_only_once() -> None:
    assert get_model() is get_model()  # lru_cache returns the very same object

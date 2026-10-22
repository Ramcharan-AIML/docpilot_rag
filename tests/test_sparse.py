"""Tests for embedding/sparse.py: FastEmbed's BM25 behaves as D-052 describes (fastembed 0.8.1).

Downloads the 90 KB "model" (stop-word lists) once into .cache/fastembed.
"""

from docpilot.embedding.sparse import (
    average_length,
    bm25_length,
    embed_sparse_documents,
    embed_sparse_query,
)


def test_stemming_matches_word_forms_and_keeps_underscore_names():
    # "validated" and "validate" share a word id (both stem to "valid"); max_length stays whole.
    document = embed_sparse_documents(["The body is validated. Use max_length."], avg_len=5.0)[0]
    query = embed_sparse_query("validate max_length")
    assert len(query["indices"]) == 2
    assert set(query["indices"]) <= set(document["indices"])


def test_stop_words_are_not_counted():
    assert bm25_length("the body of the request") == 2  # "body", "request"
    assert average_length(["the body of the request", "max_length"]) == 1.5


def test_repeats_saturate_and_long_chunks_weigh_less():
    once, ten_times = embed_sparse_documents(["docker", " ".join(["docker"] * 10)], avg_len=1.0)
    assert ten_times["values"][0] < 10 * once["values"][0]  # saturation
    short, long = embed_sparse_documents(["docker", "docker " + "image " * 9], avg_len=5.0)
    assert long["values"][long["indices"].index(short["indices"][0])] < short["values"][0]

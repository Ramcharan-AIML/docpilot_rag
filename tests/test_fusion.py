"""Tests for retrieval/fusion.py (made-up ids) and retrieval/hybrid.py (tiny local Qdrant)."""

from pathlib import Path

import pytest

from docpilot.ingestion.chunkers.base import Chunk
from docpilot.retrieval.fusion import reciprocal_rank_fusion
from docpilot.retrieval.hybrid import hybrid_search_manual
from docpilot.store.qdrant_store import (
    add_chunks,
    create_fresh_collection,
    get_client,
    search_hybrid,
)


def test_first_in_both_lists_wins():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["a", "c", "b"]], k=60)
    assert fused[0] == ("a", pytest.approx(2 / 61))


def test_id_in_only_one_list_still_appears():
    ids = [item_id for item_id, _ in reciprocal_rank_fusion([["a", "b"], ["c"]])]
    assert sorted(ids) == ["a", "b", "c"]


def test_equal_ranks_give_equal_scores():
    # "a" is 1st in list one, "b" is 1st in list two: same ranks, so the same score.
    scores = dict(reciprocal_rank_fusion([["a"], ["b"]]))
    assert scores["a"] == scores["b"]


def test_worked_example_from_the_teaching_notes():
    # teaching/phase_3_retrieval.md section 3: A (1st, 3rd), B (2nd, -), C (-, 1st) -> A, C, B
    fused = reciprocal_rank_fusion([["A", "B", "x"], ["C", "y", "A"]], k=60)
    assert [item_id for item_id, _ in fused][:3] == ["A", "C", "B"]


def test_small_k_makes_rank_one_worth_more():
    # 1st in one list vs 4th in both: small k trusts the single 1st, big k trusts agreement.
    # k=1: solo 1/2 = 0.50 > both 2/5 = 0.40.  k=60: solo 1/61 = 0.016 < both 2/64 = 0.031.
    lists = [["solo", "p", "q", "both"], ["r", "s", "t", "both"]]
    small, big = dict(reciprocal_rank_fusion(lists, k=1)), dict(reciprocal_rank_fusion(lists))
    assert small["solo"] > small["both"]
    assert big["solo"] < big["both"]


def test_k_must_be_positive():
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([["a"]], k=0)


def test_hybrid_finds_what_only_one_searcher_finds(tmp_path: Path):
    # Chunk 0 matches the dense query; chunk 2 holds the only rare word of the sparse query.
    client = get_client(tmp_path / "qdrant")
    try:
        create_fresh_collection(client, "t", dimension=4)
        chunks = [Chunk(text=f"text {i}", source="a.md", chunk_number=i) for i in range(3)]
        vectors = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]]
        sparse = [
            {"indices": [1], "values": [1.0]},
            {"indices": [1], "values": [1.0]},
            {"indices": [1, 7], "values": [1.0, 1.0]},
        ]
        add_chunks(client, "t", chunks, vectors, sparse)
        # candidates=1: each searcher sends only its 1st (dense alone would return all 3).
        hits = hybrid_search_manual(
            client,
            "t",
            [1.0, 0.0, 0.0, 0.0],
            {"indices": [7], "values": [1.0]},
            top_k=2,
            candidates=1,
        )
    finally:
        client.close()
    assert {hit["chunk_number"] for hit in hits} == {0, 2}
    assert hits[0]["dense_rank"] == 1 and hits[0]["sparse_rank"] is None  # tie: dense first
    assert hits[1]["sparse_rank"] == 1


def test_server_fusion_gives_the_same_scores_as_manual(tmp_path: Path):
    # Step 3.4: our k=60 must equal Qdrant's k=61 (Qdrant uses 1/(k + rank - 1)).
    # Local mode runs qdrant-client's Python copy of the same formula as the server.
    client = get_client(tmp_path / "qdrant")
    try:
        create_fresh_collection(client, "t", dimension=4)
        chunks = [Chunk(text=f"text {i}", source="a.md", chunk_number=i) for i in range(3)]
        vectors = [[1.0, 0.0, 0.0, 0.0], [0.6, 0.8, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]]
        sparse = [
            {"indices": [1], "values": [1.0]},
            {"indices": [1, 7], "values": [1.0, 1.0]},
            {"indices": [7], "values": [1.0]},
        ]
        add_chunks(client, "t", chunks, vectors, sparse)
        args = ("t", [1.0, 0.0, 0.0, 0.0], {"indices": [7], "values": [1.0]})
        manual = hybrid_search_manual(client, *args, top_k=3, candidates=3, rrf_k=60)
        server = search_hybrid(client, *args, top_k=3, candidates=3, rrf_k=60)
    finally:
        client.close()
    assert [h["chunk_number"] for h in server] == [h["chunk_number"] for h in manual]
    assert [h["score"] for h in server] == pytest.approx([h["score"] for h in manual])

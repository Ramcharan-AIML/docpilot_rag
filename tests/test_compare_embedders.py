"""Tests for the step 3.7 model registry and the store helper that reads chunks back."""

from pathlib import Path

from docpilot.ingestion.chunkers.base import Chunk
from docpilot.store.qdrant_store import (
    add_chunks,
    all_payloads,
    create_fresh_collection,
    get_client,
)
from evals.compare_embedders import EMBEDDERS


def test_every_model_is_pinned_to_a_full_commit():
    for spec in EMBEDDERS.values():
        assert len(spec["revision"]) == 40, spec["model"]


def test_prefix_rules_from_the_model_cards():
    # The classic bug: a model trained with prefixes gets none (or the wrong side gets one).
    assert EMBEDDERS["e5-base"]["query_prefix"] == "query: "
    assert EMBEDDERS["e5-base"]["doc_prefix"] == "passage: "
    assert EMBEDDERS["nomic"]["doc_prefix"] == "search_document: "
    assert EMBEDDERS["bge-base"]["doc_prefix"] == ""  # BGE: question side only
    assert EMBEDDERS["bge-m3"]["query_prefix"] == ""


def test_all_payloads_gives_back_every_chunk(tmp_path: Path):
    client = get_client(tmp_path / "qdrant")
    try:
        create_fresh_collection(client, "t", dimension=2)
        chunks = [Chunk(text=f"t{i}", source="a.md", chunk_number=i) for i in range(300)]
        add_chunks(client, "t", chunks, [[1.0, 0.0]] * 300)
        payloads = all_payloads(client, "t")  # 300 > one page of 256
    finally:
        client.close()
    assert sorted(Chunk(**p).chunk_number for p in payloads) == list(range(300))

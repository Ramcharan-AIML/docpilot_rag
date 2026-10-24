"""Tests for vector_store.py with tiny 4-number vectors (no model needed, runs in a moment).

Each test gets its own Qdrant folder inside pytest's tmp_path, and closes the client after.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from docpilot import config
from docpilot.ingestion.chunkers.base import Chunk
from docpilot.store import qdrant_store
from docpilot.store.qdrant_store import (
    add_chunks,
    create_fresh_collection,
    get_client,
    make_point_id,
    search,
    search_sparse,
)

NAME = "test_collection"


@pytest.fixture
def client(tmp_path: Path) -> Iterator[QdrantClient]:
    qdrant = get_client(tmp_path / "qdrant")
    create_fresh_collection(qdrant, NAME, dimension=4)
    yield qdrant
    qdrant.close()  # release the folder lock


def three_chunks() -> tuple[list[Chunk], list[list[float]]]:
    chunks = [Chunk(text=f"text {i}", source="a.md", chunk_number=i) for i in range(3)]
    vectors = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]]
    return chunks, vectors


def test_point_id_is_the_same_every_time() -> None:
    chunk = Chunk(text="anything", source="a.md", chunk_number=0)

    assert make_point_id(chunk) == make_point_id(chunk)
    assert make_point_id(chunk) != make_point_id(Chunk("anything", "a.md", 1))


def test_search_returns_closest_first_with_payload(client: QdrantClient) -> None:
    chunks, vectors = three_chunks()
    add_chunks(client, NAME, chunks, vectors)

    hits = search(client, NAME, [0.0, 0.9, 0.1, 0.0], top_k=2)

    assert len(hits) == 2
    assert hits[0]["text"] == "text 1"  # the query points almost exactly at chunk 1
    assert hits[0]["source"] == "a.md"
    assert hits[0]["score"] >= hits[1]["score"]


def test_adding_twice_does_not_duplicate(client: QdrantClient) -> None:
    chunks, vectors = three_chunks()
    add_chunks(client, NAME, chunks, vectors)
    add_chunks(client, NAME, chunks, vectors)  # same ids -> overwritten, not added

    assert client.count(NAME).count == 3


def test_fresh_collection_is_empty(client: QdrantClient) -> None:
    chunks, vectors = three_chunks()
    add_chunks(client, NAME, chunks, vectors)

    create_fresh_collection(client, NAME, dimension=4)

    assert client.count(NAME).count == 0


def test_mismatched_lengths_raise(client: QdrantClient) -> None:
    chunks, vectors = three_chunks()

    with pytest.raises(ValueError):
        add_chunks(client, NAME, chunks, vectors[:2])  # 3 chunks, 2 vectors


def test_get_client_server_mode_only_without_a_path(monkeypatch, tmp_path):
    # Step 3.1: QDRANT_URL set -> server (Docker); an explicit path always means local mode.
    opened = []
    monkeypatch.setattr(qdrant_store, "QdrantClient", lambda **kwargs: opened.append(kwargs))
    monkeypatch.setattr(config, "QDRANT_URL", "http://localhost:6333")
    get_client()
    get_client(tmp_path)
    monkeypatch.setattr(config, "QDRANT_URL", "")
    get_client()
    assert opened == [
        {"url": "http://localhost:6333", "timeout": 60},
        {"path": str(tmp_path)},
        {"path": str(config.QDRANT_PATH)},
    ]


def test_sparse_search_finds_the_rare_word(client: QdrantClient) -> None:
    # Step 3.2: made-up BM25 word ids. Word 7 is rare (one chunk); word 1 is in every chunk,
    # so Qdrant's IDF makes it nearly worthless.
    chunks, vectors = three_chunks()
    sparse = [
        {"indices": [1, 2], "values": [1.0, 1.0]},
        {"indices": [1, 7], "values": [1.0, 1.0]},
        {"indices": [1, 3], "values": [1.0, 1.0]},
    ]
    add_chunks(client, NAME, chunks, vectors, sparse)
    hits = search_sparse(client, NAME, {"indices": [1, 7], "values": [1.0, 1.0]}, top_k=3)
    assert hits[0]["chunk_number"] == 1  # the chunk with the rare word wins
    assert search(client, NAME, [1.0, 0.0, 0.0, 0.0], top_k=1)[0]["chunk_number"] == 0


def test_sparse_vectors_must_match_chunks(client: QdrantClient) -> None:
    chunks, vectors = three_chunks()
    with pytest.raises(ValueError):
        add_chunks(client, NAME, chunks, vectors, [{"indices": [1], "values": [1.0]}])


def test_cold_collection_still_searches_and_filters(tmp_path: Path) -> None:
    # A5: the uploads layout (on disk + payload indexes). Local mode accepts the settings;
    # the real server applies them (checked by hand against Qdrant 1.19.1 in Docker).
    qdrant = get_client(tmp_path / "cold")
    try:
        qdrant_store.ensure_collection(qdrant, "uploads", dimension=4, cold=True)
        qdrant_store.ensure_collection(qdrant, "uploads", dimension=4, cold=True)  # no error
        chunks, vectors = three_chunks()
        add_chunks(qdrant, "uploads", chunks, vectors)
        hits = search(qdrant, "uploads", [0.0, 0.9, 0.1, 0.0], top_k=1)
        assert hits[0]["text"] == "text 1"
        assert search(qdrant, "uploads", [1.0, 0, 0, 0], 3, qdrant_store.chat_filter("x")) == []
    finally:
        qdrant.close()

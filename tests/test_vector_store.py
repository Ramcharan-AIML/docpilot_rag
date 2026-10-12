"""Tests for vector_store.py with tiny 4-number vectors (no model needed, runs in a moment).

Each test gets its own Qdrant folder inside pytest's tmp_path, and closes the client after.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from docpilot.chunker import Chunk
from docpilot.vector_store import (
    add_chunks,
    create_fresh_collection,
    get_client,
    make_point_id,
    search,
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

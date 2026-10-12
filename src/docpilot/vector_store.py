"""Qdrant helpers: create a collection, add chunks, search.

This is the only file that talks to Qdrant. Swapping the database later means changing
this file only; the rest of the code sees plain lists and dicts.
"""

import uuid
from pathlib import Path

from qdrant_client import QdrantClient, models  # API checked on 1.19.1 (D-027)

from docpilot.chunker import Chunk


def get_client(path: Path) -> QdrantClient:
    """Local mode: Qdrant runs inside this Python process and saves to a folder.

    Only ONE client can open the folder at a time; a second one raises RuntimeError
    (D-003). Qdrant in Docker removes this limit in Phase 3. Call client.close() when done.
    """
    return QdrantClient(path=str(path))


def create_fresh_collection(client: QdrantClient, name: str, dimension: int) -> None:
    """Delete the collection if it exists, then create it empty. Makes re-runs repeatable."""
    if client.collection_exists(name):
        client.delete_collection(name)
    client.create_collection(
        collection_name=name,
        # size must equal the embedding length (384); COSINE matches how BGE was trained
        vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE),
    )
    # Workaround, found by a test on 2026-10-12 (qdrant-client 1.19.1, local mode, Windows):
    # delete_collection leaves storage.sqlite on disk and create_collection loads the OLD
    # points back. Delete every point (an empty filter matches all), then check.
    client.delete(
        collection_name=name, points_selector=models.FilterSelector(filter=models.Filter())
    )
    leftover = client.count(name, exact=True).count
    if leftover:
        raise RuntimeError(f"Collection {name!r} still has {leftover} points after reset")


def make_point_id(chunk: Chunk) -> str:
    """Same chunk -> same id on every run (uuid5 hashes "source#number"; uuid4 is random).

    Qdrant ids must be a number or a UUID, so "fastapi/query.md#3" cannot be used as is.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{chunk.source}#{chunk.chunk_number}"))


def add_chunks(
    client: QdrantClient, name: str, chunks: list[Chunk], vectors: list[list[float]]
) -> None:
    """Store each chunk's vector, with its text and source as the payload (the "label")."""
    if not chunks:
        return
    points = []
    for chunk, vector in zip(chunks, vectors, strict=True):  # strict: lengths must match
        payload = {"text": chunk.text, "source": chunk.source, "chunk_number": chunk.chunk_number}
        points.append(models.PointStruct(id=make_point_id(chunk), vector=vector, payload=payload))
    # upsert = insert, or overwrite a point with the same id (so a re-run never duplicates)
    client.upsert(collection_name=name, points=points)


def search(client: QdrantClient, name: str, query_vector: list[float], top_k: int) -> list[dict]:
    """Return the top_k closest chunks as plain dicts (text, source, chunk_number, score)."""
    response = client.query_points(
        collection_name=name, query=query_vector, limit=top_k, with_payload=True
    )
    hits = []
    for point in response.points:  # already sorted: highest score first
        hit = dict(point.payload or {})
        hit["score"] = point.score
        hits.append(hit)
    return hits

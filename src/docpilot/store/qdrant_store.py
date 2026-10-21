"""Qdrant helpers: create a collection, add chunks, search.

This is the only file that talks to Qdrant. Swapping the database later means changing
this file only; the rest of the code sees plain lists and dicts.
"""

import uuid
from dataclasses import asdict
from pathlib import Path

from qdrant_client import QdrantClient, models  # API checked on 1.19.1 (D-027)

from docpilot import config
from docpilot.ingestion.chunkers.base import Chunk

# Step 3.2: every point has two NAMED vectors. "dense" = meaning (BGE, 384 numbers);
# "sparse" = keywords (BM25 word weights). Collections built before 3.2 had one unnamed
# vector: re-ingest them.
DENSE = "dense"
SPARSE = "sparse"


def get_client(path: Path | None = None) -> QdrantClient:
    """Open Qdrant. Call client.close() when done.

    No path + config.QDRANT_URL set: server mode, Qdrant in Docker (step 3.1). Many
    processes can use it at once (API, evals, scripts).
    Otherwise local mode: Qdrant runs inside this Python process and saves to a folder
    (`path`, or config.QDRANT_PATH). Only ONE client can open the folder at a time; a
    second one raises RuntimeError (D-003). Tests and CI use local mode: no Docker there.
    """
    if path is None and config.QDRANT_URL:
        # 60 s, not the default 5 s: snapshot create/restore of a big index takes longer.
        return QdrantClient(url=config.QDRANT_URL, timeout=60)
    return QdrantClient(path=str(path or config.QDRANT_PATH))


def create_fresh_collection(client: QdrantClient, name: str, dimension: int) -> None:
    """Delete the collection if it exists, then create it empty. Makes re-runs repeatable."""
    if client.collection_exists(name):
        client.delete_collection(name)
    client.create_collection(
        collection_name=name,
        # size must equal the embedding length (384); COSINE matches how BGE was trained
        vectors_config={
            DENSE: models.VectorParams(size=dimension, distance=models.Distance.COSINE)
        },
        # IDF modifier: Qdrant computes each word's rarity over the whole collection, the
        # half of BM25 a single chunk cannot know (embedding/sparse.py has the other half).
        sparse_vectors_config={SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)},
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
    client: QdrantClient,
    name: str,
    chunks: list[Chunk],
    vectors: list[list[float]],
    sparse_vectors: list[dict] | None = None,
) -> None:
    """Store each chunk's vectors, with its text and source as the payload (the "label").

    `sparse_vectors` (BM25, step 3.2) are optional: {"indices": [...], "values": [...]}.
    """
    if not chunks:
        return
    if sparse_vectors is not None and len(sparse_vectors) != len(chunks):
        raise ValueError(f"{len(chunks)} chunks but {len(sparse_vectors)} sparse vectors")
    points = []
    for number, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
        named: dict = {DENSE: vector}  # strict zip above: lengths must match
        if sparse_vectors is not None:
            named[SPARSE] = models.SparseVector(**sparse_vectors[number])
        # Every Chunk field becomes payload (step 2.5): filter and cite by metadata later.
        payload = asdict(chunk)
        points.append(models.PointStruct(id=make_point_id(chunk), vector=named, payload=payload))
    # upsert = insert, or overwrite a point with the same id (so a re-run never duplicates)
    client.upsert(collection_name=name, points=points)


def search(client: QdrantClient, name: str, query_vector: list[float], top_k: int) -> list[dict]:
    """Meaning search: the top_k closest chunks as plain dicts (text, source, ..., score)."""
    response = client.query_points(
        collection_name=name, query=query_vector, using=DENSE, limit=top_k, with_payload=True
    )
    return to_hits(response)


def search_sparse(client: QdrantClient, name: str, sparse_query: dict, top_k: int) -> list[dict]:
    """Keyword search (BM25): the top_k chunks sharing the most valuable words with the query.

    The score is a BM25 score (0 to any number), not a cosine (0 to 1): never compare the
    two directly. That is why hybrid search (step 3.3) merges ranks, not scores.
    """
    response = client.query_points(
        collection_name=name,
        query=models.SparseVector(**sparse_query),
        using=SPARSE,
        limit=top_k,
        with_payload=True,
    )
    return to_hits(response)


def to_hits(response) -> list[dict]:
    """Qdrant points -> plain dicts (payload + score); the rest of the code sees no Qdrant."""
    hits = []
    for point in response.points:  # already sorted: highest score first
        hit = dict(point.payload or {})
        hit["score"] = point.score
        hits.append(hit)
    return hits

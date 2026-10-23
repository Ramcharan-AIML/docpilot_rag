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
    create_collection(client, name, dimension)
    # Workaround, found by a test on 2026-10-12 (qdrant-client 1.19.1, local mode, Windows):
    # delete_collection leaves storage.sqlite on disk and create_collection loads the OLD
    # points back. Delete every point (an empty filter matches all), then check.
    client.delete(
        collection_name=name, points_selector=models.FilterSelector(filter=models.Filter())
    )
    leftover = client.count(name, exact=True).count
    if leftover:
        raise RuntimeError(f"Collection {name!r} still has {leftover} points after reset")


def ensure_collection(client: QdrantClient, name: str, dimension: int) -> None:
    """Create the collection only if it is missing; never delete (D-060: the uploads
    collection grows one file at a time)."""
    if not client.collection_exists(name):
        create_collection(client, name, dimension)


def create_collection(client: QdrantClient, name: str, dimension: int) -> None:
    """The one place that defines our collection layout: dense + sparse named vectors."""
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


def delete_where(client: QdrantClient, name: str, key: str, value: str) -> None:
    """Remove every point whose payload `key` equals `value` (one file, or one whole chat).

    Re-uploading a shorter file must not leave its old extra chunks behind (point ids are
    source#number, so only the first ones would be overwritten).
    """
    if client.collection_exists(name):
        selector = models.FilterSelector(filter=field_filter(key, value))
        client.delete(collection_name=name, points_selector=selector)


def delete_source(client: QdrantClient, name: str, source: str) -> None:
    delete_where(client, name, "source", source)


def chunks_per_source(client: QdrantClient, name: str) -> dict[str, int]:
    """{source: chunk count} for a collection; {} if it does not exist yet."""
    if not client.collection_exists(name):
        return {}
    counts: dict[str, int] = {}
    for payload in all_payloads(client, name):
        counts[payload["source"]] = counts.get(payload["source"], 0) + 1
    return dict(sorted(counts.items()))


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
    extra_payload: dict | None = None,
) -> None:
    """Store each chunk's vectors, with its text and source as the payload (the "label").

    `sparse_vectors` (BM25, step 3.2) are optional: {"indices": [...], "values": [...]}.
    `extra_payload` is added to every point, e.g. {"chat_id": ...} for uploads (D-061).
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
        payload = {**asdict(chunk), **(extra_payload or {})}
        points.append(models.PointStruct(id=make_point_id(chunk), vector=named, payload=payload))
    # upsert = insert, or overwrite a point with the same id (so a re-run never duplicates)
    client.upsert(collection_name=name, points=points)


def field_filter(key: str, value: str) -> models.Filter:
    """Matches points whose payload field `key` equals `value`."""
    return models.Filter(
        must=[models.FieldCondition(key=key, match=models.MatchValue(value=value))]
    )


def chat_filter(chat_id: str) -> models.Filter | None:
    """Only one chat's uploaded files (D-061, NotebookLM style); None = no filter."""
    return field_filter("chat_id", chat_id) if chat_id else None


def search(
    client: QdrantClient,
    name: str,
    query_vector: list[float],
    top_k: int,
    query_filter: models.Filter | None = None,
) -> list[dict]:
    """Meaning search: the top_k closest chunks as plain dicts (text, source, ..., score)."""
    response = client.query_points(
        collection_name=name,
        query=query_vector,
        using=DENSE,
        limit=top_k,
        with_payload=True,
        query_filter=query_filter,
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


def search_hybrid(
    client: QdrantClient,
    name: str,
    dense_vector: list[float],
    sparse_query: dict,
    top_k: int,
    candidates: int,
    rrf_k: int,
    query_filter: models.Filter | None = None,
) -> list[dict]:
    """Hybrid search in ONE call (step 3.4): Qdrant runs both searches and the RRF itself.

    `query_filter` limits BOTH searches (e.g. one chat's files), so the RRF never sees
    chunks from outside the filter.

    `rrf_k` means the same as in retrieval/fusion.py: 1 / (k + rank). Qdrant's own formula
    is 1 / (k + rank - 1), so we send k + 1. Checked on Qdrant v1.19.1 on 2026-10-22: its
    k=61 gave the same scores as our k=60. Qdrant's default k is 2, NOT 60 (D-054).
    """
    response = client.query_points(
        collection_name=name,
        prefetch=[
            models.Prefetch(query=dense_vector, using=DENSE, limit=candidates, filter=query_filter),
            models.Prefetch(
                query=models.SparseVector(**sparse_query),
                using=SPARSE,
                limit=candidates,
                filter=query_filter,
            ),
        ],
        query=models.RrfQuery(rrf=models.Rrf(k=rrf_k + 1)),
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


def all_payloads(client: QdrantClient, name: str) -> list[dict]:
    """Every point's payload (the chunk fields), page by page. Step 3.7 re-embeds the SAME
    chunks with other models, so the comparison changes only the model."""
    payloads, offset = [], None
    while True:
        points, offset = client.scroll(
            collection_name=name, limit=256, offset=offset, with_payload=True, with_vectors=False
        )
        payloads.extend(dict(point.payload or {}) for point in points)
        if offset is None:  # no next page
            return payloads

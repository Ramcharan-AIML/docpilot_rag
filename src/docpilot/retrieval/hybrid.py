"""Hybrid search by hand: dense top N + sparse top N, merged with RRF (step 3.3).

Plan fix: the plan also lists retrieval/dense_search.py and sparse_search.py. They would only
repeat store.search() and store.search_sparse() (step 3.2), which already return plain
dicts, so this file calls the store directly.
"""

from qdrant_client import QdrantClient

from docpilot.retrieval.fusion import DEFAULT_RRF_K, reciprocal_rank_fusion
from docpilot.store.qdrant_store import search, search_hybrid, search_sparse

DEFAULT_CANDIDATES = 50  # per searcher; a chunk missing from both top 50s cannot come back


def hit_key(hit: dict) -> str:
    """One id per chunk: "source#chunk_number", the same pair make_point_id() hashes."""
    return f"{hit['source']}#{hit['chunk_number']}"


def hybrid_search_manual(
    client: QdrantClient,
    name: str,
    dense_vector: list[float],
    sparse_query: dict,
    top_k: int,
    candidates: int = DEFAULT_CANDIDATES,
    rrf_k: int = DEFAULT_RRF_K,
) -> list[dict]:
    """The top_k chunks after RRF. Takes vectors, not the question, so the caller can time
    the search without the embedding (same as the dense and sparse evals).

    Each hit's "score" becomes the RRF score (about 0.01 to 0.03, NOT a cosine). The ranks
    in each list are kept as dense_rank / sparse_rank (None = not in that top N), so a
    failure can be read: which searcher found it, and how high.
    """
    dense_hits = search(client, name, dense_vector, candidates)
    sparse_hits = search_sparse(client, name, sparse_query, candidates)
    dense_ranks = {hit_key(hit): rank for rank, hit in enumerate(dense_hits, start=1)}
    sparse_ranks = {hit_key(hit): rank for rank, hit in enumerate(sparse_hits, start=1)}
    # The same chunk comes back from both searches with the same payload: keep one copy.
    by_key = {hit_key(hit): hit for hit in sparse_hits + dense_hits}

    fused = reciprocal_rank_fusion([list(dense_ranks), list(sparse_ranks)], k=rrf_k)
    hits = []
    for key, fused_score in fused[:top_k]:
        hit = dict(by_key[key])  # a copy: never change the search results in place
        hit["score"] = fused_score
        hit["dense_rank"] = dense_ranks.get(key)
        hit["sparse_rank"] = sparse_ranks.get(key)
        hits.append(hit)
    return hits


def multi_search(
    client: QdrantClient,
    name: str,
    queries: list[tuple[list[float], dict]],
    top_k: int,
    candidates: int = DEFAULT_CANDIDATES,
    rrf_k: int = DEFAULT_RRF_K,
) -> list[dict]:
    """Step 3.6: one Qdrant hybrid search per (dense, sparse) query, then RRF over the lists.

    Used by query transforms: the question and its rewrites each give a ranked list; a
    chunk found by several of them rises, like a chunk found by both searchers in 3.3.
    """
    lists = [
        search_hybrid(client, name, dense, sparse, top_k, candidates=candidates, rrf_k=rrf_k)
        for dense, sparse in queries
    ]
    by_key: dict[str, dict] = {}
    for hits in lists:
        for hit in hits:
            by_key.setdefault(hit_key(hit), hit)
    fused = reciprocal_rank_fusion([[hit_key(h) for h in hits] for hits in lists], k=rrf_k)
    return [{**by_key[key], "score": score} for key, score in fused[:top_k]]

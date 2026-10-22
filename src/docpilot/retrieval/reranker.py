"""Reranker (step 3.5, D-055): re-score candidates by reading question and chunk TOGETHER.

Search (bi-encoder) turns question and chunk into vectors SEPARATELY, then compares them:
fast, but the model never sees both at once. A cross-encoder reads "question + chunk" as
one input and gives one relevance score: slower (one model run per chunk), more accurate.
So: search finds about 30 candidates fast, the reranker puts the best ones on top.
"""

from functools import lru_cache

from sentence_transformers import CrossEncoder  # API checked on 6.1.0 (2026-10-22)

from docpilot import config


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    """Load once (about 1.1 GB the first time, into the Hugging Face cache), then reuse."""
    return CrossEncoder(
        config.RERANKER_MODEL,
        revision=config.RERANKER_REVISION,  # pinned, like the embedding model
        max_length=config.RERANKER_MAX_TOKENS,  # longer pairs are cut, not an error
    )


def rerank(question: str, hits: list[dict], keep: int) -> list[dict]:
    """The `keep` best hits by reranker score, best first.

    Copies the hits (the caller's list is not changed). Each hit gets "rerank_score" and
    "search_rank" (its place before reranking), so we can see what the reranker moved.
    """
    if not hits:
        return []
    pairs = [(question, hit["text"]) for hit in hits]
    scores = get_reranker().predict(pairs)  # one score per (question, chunk) pair
    reranked = []
    for search_rank, (hit, score) in enumerate(zip(hits, scores, strict=True), start=1):
        reranked.append({**hit, "rerank_score": float(score), "search_rank": search_rank})
    # Sort is stable: on an exact tie the search order decides, so results are repeatable.
    reranked.sort(key=lambda hit: hit["rerank_score"], reverse=True)
    return reranked[:keep]

"""One front door for retrieval (step 3.10): `retrieve(question, client, settings)`.

The app, the API and the evals call this one function, so they all search the same way.
The defaults are the Phase 3 winners: Qdrant hybrid (dense + BM25, RRF k=60, D-054), then
the MiniLM reranker on the top 20 (D-055), keep 4 for the LLM. No query transform (D-056).
"""

import time
from dataclasses import dataclass

from qdrant_client import QdrantClient

from docpilot import config
from docpilot.embedding.dense import embed_query
from docpilot.embedding.sparse import embed_sparse_query
from docpilot.retrieval.fusion import DEFAULT_RRF_K
from docpilot.retrieval.hybrid import DEFAULT_CANDIDATES
from docpilot.retrieval.reranker import rerank
from docpilot.store.qdrant_store import search, search_hybrid


@dataclass(frozen=True)
class RetrievalSettings:
    hybrid: bool = True  # False = dense only (the Phase 1/2 app)
    rerank_candidates: int = 20  # 0 = no reranker
    reranker: str = config.RERANKER
    top_k: int = config.TOP_K  # chunks given to the LLM
    candidates_per_searcher: int = DEFAULT_CANDIDATES
    rrf_k: int = DEFAULT_RRF_K
    collection: str = config.COLLECTION_NAME


BEST = RetrievalSettings()  # the Phase 3 winner
DENSE_ONLY = RetrievalSettings(hybrid=False, rerank_candidates=0)  # the old app


def retrieve(
    question: str,
    client: QdrantClient,
    settings: RetrievalSettings = BEST,
    timings: dict[str, float] | None = None,
) -> list[dict]:
    """The top_k chunks for `question`, best first. Fills `timings` (ms per stage) if given."""

    def lap(stage: str, start: float) -> None:
        if timings is not None:
            timings[stage] = round((time.perf_counter() - start) * 1000, 1)

    start = time.perf_counter()
    vector = embed_query(question)
    sparse = embed_sparse_query(question) if settings.hybrid else None
    lap("embed_query", start)

    # Search returns more than top_k when the reranker will choose among them.
    fetch = max(settings.rerank_candidates, settings.top_k)
    start = time.perf_counter()
    if settings.hybrid:
        hits = search_hybrid(
            client,
            settings.collection,
            vector,
            sparse,
            fetch,
            candidates=settings.candidates_per_searcher,
            rrf_k=settings.rrf_k,
        )
    else:
        hits = search(client, settings.collection, vector, fetch)
    lap("search", start)

    if settings.rerank_candidates:
        start = time.perf_counter()
        hits = rerank(question, hits, settings.top_k, settings.reranker)
        lap("rerank", start)
    return hits[: settings.top_k]

"""Step 3.4 check: do manual RRF and Qdrant's RRF give the same top 5? (no LLM, no MLflow)

Run: python -m evals.compare_fusion
For the first 10 answerable dev questions it prints how many of the top-5 chunks are the
same, and whether the ORDER is the same too. Rows: our k=60 vs Qdrant with the same k, and
vs Qdrant's own default k (to show why the default must not be used).
"""

import argparse

from qdrant_client import models

from docpilot.embedding.dense import embed_query
from docpilot.embedding.sparse import embed_sparse_query
from docpilot.retrieval.fusion import DEFAULT_RRF_K
from docpilot.retrieval.hybrid import DEFAULT_CANDIDATES, hit_key, hybrid_search_manual
from docpilot.store.qdrant_store import DENSE, SPARSE, get_client, search_hybrid, to_hits
from evals.common import load_split

TOP = 5


def qdrant_default_k(client, name, vector, sparse_query) -> list[dict]:
    """Qdrant RRF with NO k given: what you get if you copy the docs example as is."""
    response = client.query_points(
        collection_name=name,
        prefetch=[
            models.Prefetch(query=vector, using=DENSE, limit=DEFAULT_CANDIDATES),
            models.Prefetch(
                query=models.SparseVector(**sparse_query), using=SPARSE, limit=DEFAULT_CANDIDATES
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=TOP,
        with_payload=True,
    )
    return to_hits(response)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manual RRF vs Qdrant RRF, top 5 ids.")
    parser.add_argument("--collection", default="docpilot_v1_ft200")
    parser.add_argument("--n", type=int, default=10)
    args = parser.parse_args()

    items = [item for item in load_split("dev") if item["should_answer"]][: args.n]
    client = get_client()
    same_set = {"server k=60": 0, "server default k": 0}
    same_order = dict.fromkeys(same_set, 0)
    try:
        print(f"{'question':10}{'server k=60':>22}{'server default k':>22}")
        for item in items:
            vector = embed_query(item["question"])
            sparse_query = embed_sparse_query(item["question"])
            manual = hybrid_search_manual(
                client, args.collection, vector, sparse_query, TOP, rrf_k=DEFAULT_RRF_K
            )
            server = search_hybrid(
                client,
                args.collection,
                vector,
                sparse_query,
                TOP,
                candidates=DEFAULT_CANDIDATES,
                rrf_k=DEFAULT_RRF_K,
            )
            default = qdrant_default_k(client, args.collection, vector, sparse_query)
            manual_ids = [hit_key(hit) for hit in manual]
            cells = []
            for label, hits in (("server k=60", server), ("server default k", default)):
                ids = [hit_key(hit) for hit in hits]
                overlap = len(set(ids) & set(manual_ids))
                in_order = ids == manual_ids
                same_set[label] += overlap == TOP
                same_order[label] += in_order
                cells.append(f"{overlap}/5 same, order {'same' if in_order else 'DIFF'}")
            print(f"{item['id']:10}" + "".join(f"{cell:>22}" for cell in cells))
    finally:
        client.close()
    for label in same_set:
        print(f"{label}: same 5 chunks {same_set[label]}/{len(items)}, ", end="")
        print(f"same order {same_order[label]}/{len(items)}")


if __name__ == "__main__":
    main()

"""Score retrieval against the golden set: Recall@k, MRR, nDCG@5 (no LLM, no cost).

Run: python -m evals.run_retrieval_eval --split dev --config-id C0
Saves evals/results/<date>_<config>_<split>_retrieval.json and prints a small table.
"""

import argparse
from collections import defaultdict
from pathlib import Path

from docpilot import config
from docpilot.embedding.dense import embed_query
from docpilot.embedding.sparse import embed_sparse_query
from docpilot.ingestion.chunkers.parent_child import lift_to_parents, load_parents
from docpilot.ingestion.manifest import load_manifest
from docpilot.retrieval.fusion import DEFAULT_RRF_K
from docpilot.retrieval.hybrid import DEFAULT_CANDIDATES, hybrid_search_manual
from docpilot.retrieval.reranker import rerank
from docpilot.store.qdrant_store import get_client, search, search_hybrid, search_sparse
from evals.common import base_record, load_golden_file, load_split, save_result, to_json
from evals.matching import MIN_OVERLAP, relevance_list
from evals.metrics import (
    mean,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
    strict_recall_at_k,
)
from evals.timing import StageTimes
from evals.tracking import log_record

# Fetch 10 so we can report @1, @3 and @5 from one search. ask() still uses TOP_K (4).
SEARCH_K = 10
METRIC_NAMES = ("recall@1", "recall@3", "recall@5", "strict_recall@5", "rr", "ndcg@5")


def score_item(item: dict, hits: list[dict]) -> dict:
    """All metrics for one question, plus what was retrieved (for reading failures)."""
    relevance = relevance_list(hits, item["evidence"], MIN_OVERLAP)
    n_evidence = len(item["evidence"])
    return {
        "id": item["id"],
        "type": item["type"],
        "domain": item["domain"],
        "relevance": relevance,
        "recall@1": recall_at_k(relevance, 1),
        "recall@3": recall_at_k(relevance, 3),
        "recall@5": recall_at_k(relevance, 5),
        "strict_recall@5": strict_recall_at_k(relevance, 5, n_evidence),
        "rr": reciprocal_rank(relevance),
        "ndcg@5": ndcg_at_k(relevance, 5, n_evidence),
        # source#chunk and score only, no chunk text: enough to find the chunk again
        "retrieved": [f"{h['source']}#{h['chunk_number']} {h['score']:.3f}" for h in hits],
    }


def aggregate(rows: list[dict]) -> dict:
    """Mean of every metric over `rows`; MRR is the mean of the reciprocal ranks."""
    summary = {"n": len(rows)}
    for name in METRIC_NAMES:
        summary["mrr" if name == "rr" else name] = round(mean([r[name] for r in rows]), 3)
    return summary


def print_table(record: dict) -> None:
    """One line overall, then one line per domain and one per question type."""
    columns = ("n", "recall@1", "recall@3", "recall@5", "strict_recall@5", "mrr", "ndcg@5")
    print(f"\n{record['config_id']} on {record['split']}  ({record['git_commit']})")
    print(f"{'':18}" + "".join(f"{c:>16}" for c in columns))
    domains = {f"[{name}]": summary for name, summary in record["per_domain"].items()}
    groups = {"OVERALL": record["overall"], **domains, **record["per_type"]}
    for name, summary in groups.items():
        print(f"{name:18}" + "".join(f"{summary[c]:>16}" for c in columns))
    latency = record["search_latency_ms"]
    print(f"\nsearch latency (warm, n={latency['n']}): ", end="")
    print(f"p50 {latency['p50']} ms, p95 {latency['p95']} ms")
    for stage, times in record["stage_latency_ms"].items():
        print(f"  {stage:8} p50 {times['p50']:>8} ms   p95 {times['p95']:>8} ms")


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieval eval on the golden set.")
    parser.add_argument("--collection", default=config.COLLECTION_NAME)
    parser.add_argument("--split", default="dev", choices=["dev", "test"])
    parser.add_argument("--config-id", default="C0")
    parser.add_argument(
        "--ablation", action="store_true", help="mark this run for evals/ABLATION.md"
    )
    # Step 2.10, CI eval gate: another exam (evals/golden/ci.jsonl on the fixture corpus),
    # saved to a chosen file and NOT logged to MLflow (a gate run is a check, not a result).
    # Step 3.2: which search answers. dense = meaning (BGE); sparse = keywords (BM25).
    # Step 3.3: hybrid = both, merged with hand-written RRF (retrieval/hybrid.py).
    # Step 3.4: hybrid-server = the same, but Qdrant does the fusion in one call.
    parser.add_argument(
        "--retriever", default="dense", choices=["dense", "sparse", "hybrid", "hybrid-server"]
    )
    parser.add_argument("--rrf-k", type=int, default=DEFAULT_RRF_K, help="hybrid only")
    parser.add_argument(
        "--candidates", type=int, default=DEFAULT_CANDIDATES, help="hybrid only: per searcher"
    )
    # Step 3.5: rerank the top N search results with the cross-encoder (0 = no reranker).
    parser.add_argument("--rerank", type=int, default=0, help="candidates to rerank, e.g. 30")
    parser.add_argument("--golden", type=Path, help="score this golden file, not --split")
    parser.add_argument("--output", type=Path, help="save the result here; skip MLflow")
    args = parser.parse_args()

    golden = load_golden_file(args.golden) if args.golden else load_split(args.split)
    split = args.golden.stem if args.golden else args.split
    # Unanswerable items have no evidence, so retrieval cannot be scored for them;
    # they are tested by the abstention check instead.
    items = [item for item in golden if item["should_answer"]]
    # Load the models now, so the first question is not a cold number.
    embed_query("warm-up")
    embed_sparse_query("warm-up")
    if args.rerank:
        rerank("warm-up", [{"text": "warm-up"}], keep=1)

    # Parent-child (plan 2.6.3): score the PARENT text, the text the LLM will read. Found
    # in the collection's manifest, so it cannot be forgotten on the command line.
    manifest = load_manifest(args.collection) or {}
    parents = load_parents(manifest["parents_file"]) if "parents_file" in manifest else None
    # Several children can share a parent: fetch more, so 10 different parents remain.
    fetch_k = SEARCH_K * 3 if parents else SEARCH_K
    # With a reranker, search returns N candidates and the reranker keeps the best 10.
    keep_after_search = args.rerank or SEARCH_K
    if args.rerank:
        fetch_k = max(fetch_k, args.rerank * 3 if parents else args.rerank)

    client = get_client()
    rows, times = [], StageTimes()
    try:
        for item in items:
            question = item["question"]
            # Stage 1, embed: the question becomes the vector(s) this searcher needs.
            with times.measure("embed"):
                vector = embed_query(question) if args.retriever != "sparse" else None
                sparse_query = embed_sparse_query(question) if args.retriever != "dense" else None
            # Stage 2, search (+ fusion for hybrid, + parent lookup for parent-child).
            with times.measure("search"):
                if args.retriever in ("hybrid", "hybrid-server"):
                    hybrid = hybrid_search_manual if args.retriever == "hybrid" else search_hybrid
                    hits = hybrid(
                        client,
                        args.collection,
                        vector,
                        sparse_query,
                        fetch_k,
                        candidates=args.candidates,
                        rrf_k=args.rrf_k,
                    )
                elif args.retriever == "sparse":
                    hits = search_sparse(client, args.collection, sparse_query, fetch_k)
                else:
                    hits = search(client, args.collection, vector, fetch_k)
                if parents:
                    hits = lift_to_parents(hits, parents, keep_after_search)
            # Stage 3, rerank: the cross-encoder re-orders the N candidates, keeps the top 10.
            if args.rerank:
                with times.measure("rerank"):
                    hits = rerank(question, hits[: args.rerank], keep=SEARCH_K)
            rows.append(score_item(item, hits))
    finally:
        client.close()

    by_type, by_domain = defaultdict(list), defaultdict(list)
    for row in rows:
        by_type[row["type"]].append(row)
        by_domain[row["domain"]].append(row)  # plan 2.9: per-domain table (D-030)

    record = base_record(args.config_id, split, "retrieval", args.collection)
    if args.golden:
        record["settings"]["golden_version"] = f"file {args.golden.name}"
    record["settings"].update(
        {
            "search_k": SEARCH_K,
            "min_overlap": MIN_OVERLAP,
            "scored_on": "parent" if parents else "chunk",
            "retriever": args.retriever,
        }
    )
    if args.rerank:
        record["settings"].update(
            {
                "rerank_candidates": args.rerank,
                "reranker": config.RERANKER_MODEL,
                "reranker_revision": config.RERANKER_REVISION,
            }
        )
    if args.retriever.startswith("hybrid"):
        record["settings"].update({"rrf_k": args.rrf_k, "candidates": args.candidates})
    record["overall"] = aggregate(rows)
    record["per_type"] = {name: aggregate(group) for name, group in sorted(by_type.items())}
    record["per_domain"] = {name: aggregate(group) for name, group in sorted(by_domain.items())}
    # search_latency_ms keeps its old meaning (search only), so old rows stay comparable.
    stages = times.summary()
    record["search_latency_ms"] = stages["search"]
    record["stage_latency_ms"] = stages  # step 3.5: embed / search / rerank, warm
    record["per_question"] = rows
    print_table(record)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(to_json(record), encoding="utf-8")
        print(f"saved {args.output}")
        return
    path = save_result(record)
    run_id = log_record(record, path, ablation=args.ablation)  # MLflow (D-036)
    print(f"saved {path}")
    print(f"logged to MLflow: run {run_id} (open with: mlflow ui)")


if __name__ == "__main__":
    main()

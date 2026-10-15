"""Score retrieval against the golden set: Recall@k, MRR, nDCG@5 (no LLM, no cost).

Run: python -m evals.run_retrieval_eval --split dev --config-id C0
Saves evals/results/<date>_<config>_<split>_retrieval.json and prints a small table.
"""

import argparse
import time
from collections import defaultdict

from docpilot import config
from docpilot.embedder import embed_query
from docpilot.rag import elapsed_ms
from docpilot.vector_store import get_client, search
from evals.common import base_record, load_split, save_result
from evals.matching import MIN_OVERLAP, relevance_list
from evals.metrics import (
    mean,
    ndcg_at_k,
    percentile,
    recall_at_k,
    reciprocal_rank,
    strict_recall_at_k,
)

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
    """One line overall, then one line per question type."""
    columns = ("n", "recall@1", "recall@3", "recall@5", "strict_recall@5", "mrr", "ndcg@5")
    print(f"\n{record['config_id']} on {record['split']}  ({record['git_commit']})")
    print(f"{'':18}" + "".join(f"{c:>16}" for c in columns))
    groups = {"OVERALL": record["overall"], **record["per_type"]}
    for name, summary in groups.items():
        print(f"{name:18}" + "".join(f"{summary[c]:>16}" for c in columns))
    latency = record["search_latency_ms"]
    print(f"\nsearch latency (warm, n={latency['n']}): ", end="")
    print(f"p50 {latency['p50']} ms, p95 {latency['p95']} ms")


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieval eval on the golden set.")
    parser.add_argument("--collection", default=config.COLLECTION_NAME)
    parser.add_argument("--split", default="dev", choices=["dev", "test"])
    parser.add_argument("--config-id", default="C0")
    args = parser.parse_args()

    # Unanswerable items have no evidence, so retrieval cannot be scored for them;
    # they are tested by the abstention check instead.
    items = [item for item in load_split(args.split) if item["should_answer"]]
    embed_query("warm-up")  # load the model now, so the first question is not a cold number

    client = get_client(config.QDRANT_PATH)
    rows, search_times = [], []
    try:
        for item in items:
            vector = embed_query(item["question"])
            start = time.perf_counter()
            hits = search(client, args.collection, vector, SEARCH_K)
            search_times.append(elapsed_ms(start))
            rows.append(score_item(item, hits))
    finally:
        client.close()

    by_type = defaultdict(list)
    for row in rows:
        by_type[row["type"]].append(row)

    record = base_record(args.config_id, args.split, "retrieval")
    record["collection"] = args.collection
    record["settings"].update({"search_k": SEARCH_K, "min_overlap": MIN_OVERLAP})
    record["overall"] = aggregate(rows)
    record["per_type"] = {name: aggregate(group) for name, group in sorted(by_type.items())}
    record["search_latency_ms"] = {
        "n": len(search_times),
        "p50": percentile(search_times, 50),
        "p95": percentile(search_times, 95),
    }
    record["per_question"] = rows
    path = save_result(record)
    print_table(record)
    print(f"saved {path}")


if __name__ == "__main__":
    main()

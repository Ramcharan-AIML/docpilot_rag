"""Latency baseline: p50/p95 per stage of the full ask() (D-031, primer_latency.md).

Run: python -m evals.run_latency --split dev --config-id C0
Uses one LLM call per question (plus one warm-up), so it is run by hand, never in CI.
"""

import argparse
import time

from docpilot import config
from docpilot.llm import get_llm_client
from docpilot.vector_store import get_client
from evals.common import ask_with_retries, base_record, load_split, save_result
from evals.metrics import percentile
from evals.tracking import log_record

STAGES = ("embed_query", "search", "llm", "total")
HARDWARE = "laptop CPU (Windows 11, no GPU used)"


def summarise(values: list[float]) -> dict:
    """n, p50, p95 and max: max shows how far the single worst case is from p95."""
    return {
        "n": len(values),
        "p50": percentile(values, 50),
        "p95": percentile(values, 95),
        "max": max(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Latency baseline of ask().")
    parser.add_argument("--split", default="dev", choices=["dev", "test"])
    parser.add_argument("--config-id", default="C0")
    parser.add_argument(
        "--ablation", action="store_true", help="mark this run for evals/ABLATION.md"
    )
    parser.add_argument("--sleep", type=float, default=2.0, help="seconds between LLM calls")
    parser.add_argument("--limit", type=int, default=0, help="only the first N items (0 = all)")
    args = parser.parse_args()

    items = load_split(args.split)  # all items: unanswerable ones cost time too
    if args.limit:
        items = items[: args.limit]

    qdrant_client = get_client(config.QDRANT_PATH)
    llm_client = get_llm_client()
    rows = []
    try:
        # Warm-up: loads the embedding model and opens the HTTPS connection. Not recorded:
        # we measure what a user sees once the service is running (cold start is separate).
        ask_with_retries("warm-up question", qdrant_client, llm_client)
        for number, item in enumerate(items, start=1):
            time.sleep(args.sleep)  # stay under the free-tier requests-per-minute limit
            result = ask_with_retries(item["question"], qdrant_client, llm_client)
            timings = result["timings_ms"]
            rows.append(
                {
                    "id": item["id"],
                    **{stage: timings.get(stage) for stage in STAGES},
                    "retries_429": result["retries_429"],
                    "wall_ms": result["wall_ms"],  # includes any waiting after a 429
                }
            )
            print(f"{number}/{len(items)} {item['id']} total {timings['total']} ms")
    finally:
        qdrant_client.close()

    record = base_record(args.config_id, args.split, "latency")
    record["settings"].update(
        {
            "hardware": HARDWARE,
            "llm_provider": config.LLM_PROVIDER,
            "llm_model": config.LLM_MODEL,
            "warm_up_calls": 1,
            "sleep_between_calls_s": args.sleep,
        }
    )
    # A stage can be missing (no LLM call when the index is empty): skip None values.
    record["per_stage_ms"] = {
        stage: summarise([row[stage] for row in rows if row[stage] is not None]) for stage in STAGES
    }
    record["per_stage_ms"]["wall_with_retries"] = summarise([row["wall_ms"] for row in rows])
    record["retries_429_total"] = sum(row["retries_429"] for row in rows)
    record["per_question"] = rows
    path = save_result(record)
    run_id = log_record(record, path, ablation=args.ablation)  # MLflow (D-036)

    print(f"\n{args.config_id} latency on {args.split}, warm, {HARDWARE}, {config.LLM_MODEL}")
    for stage, summary in record["per_stage_ms"].items():
        print(
            f"{stage:18} n={summary['n']}  p50 {summary['p50']} ms  "
            f"p95 {summary['p95']} ms  max {summary['max']} ms"
        )
    print(f"429 retries: {record['retries_429_total']}")
    print(f"saved {path}")
    print(f"logged to MLflow: run {run_id} (open with: mlflow ui)")


if __name__ == "__main__":
    main()

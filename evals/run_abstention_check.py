"""Abstention check: does DocPilot say "not found" exactly when it should? (no judge)

Run: python -m evals.run_abstention_check --split dev --config-id C0
Deterministic marking: search the answer for config.NOT_FOUND_PHRASE. One LLM call per
question, so it is run by hand, never in CI.
"""

import argparse
import time

from docpilot import config
from docpilot.llm.client import get_llm_client
from docpilot.store.qdrant_store import get_client
from evals.common import ask_with_retries, base_record, load_split, save_result
from evals.tracking import log_record

ANSWER_PREVIEW_CHARS = 300  # enough to read why it failed, short enough for a diff


def said_not_found(answer: str) -> bool:
    """True if the answer contains the exact abstention sentence (D-008, config)."""
    return config.NOT_FOUND_PHRASE in answer


def score(rows: list[dict]) -> dict:
    """Overall accuracy plus the two ways to be wrong, which mean different things.

    - false_answer: should refuse but answered -> risk of a made-up answer
    - false_refusal: should answer but refused -> the user gets nothing
    """
    unanswerable = [r for r in rows if not r["should_answer"]]
    answerable = [r for r in rows if r["should_answer"]]
    return {
        "n": len(rows),
        "accuracy": round(sum(r["correct"] for r in rows) / len(rows), 3) if rows else 0.0,
        "unanswerable_n": len(unanswerable),
        "false_answer": sum(not r["said_not_found"] for r in unanswerable),
        "answerable_n": len(answerable),
        "false_refusal": sum(r["said_not_found"] for r in answerable),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Abstention accuracy on the golden set.")
    parser.add_argument("--split", default="dev", choices=["dev", "test"])
    parser.add_argument("--config-id", default="C0")
    parser.add_argument("--collection", default=config.COLLECTION_NAME)
    parser.add_argument(
        "--ablation", action="store_true", help="mark this run for evals/ABLATION.md"
    )
    parser.add_argument("--sleep", type=float, default=2.0, help="seconds between LLM calls")
    parser.add_argument("--limit", type=int, default=0, help="only the first N items (0 = all)")
    args = parser.parse_args()

    items = load_split(args.split)
    if args.limit:
        items = items[: args.limit]

    qdrant_client = get_client(config.QDRANT_PATH)
    llm_client = get_llm_client()
    rows = []
    try:
        for number, item in enumerate(items, start=1):
            if number > 1:
                time.sleep(args.sleep)  # stay under the free-tier requests-per-minute limit
            answer = ask_with_retries(
                item["question"], qdrant_client, llm_client, collection=args.collection
            )["answer"]
            refused = said_not_found(answer)
            rows.append(
                {
                    "id": item["id"],
                    "type": item["type"],
                    "should_answer": item["should_answer"],
                    "said_not_found": refused,
                    "correct": refused == (not item["should_answer"]),
                    "answer_preview": answer[:ANSWER_PREVIEW_CHARS],
                }
            )
            print(f"{number}/{len(items)} {item['id']} {'ok' if rows[-1]['correct'] else 'WRONG'}")
    finally:
        qdrant_client.close()

    record = base_record(args.config_id, args.split, "abstention", args.collection)
    record["settings"].update({"llm_provider": config.LLM_PROVIDER, "llm_model": config.LLM_MODEL})
    record["overall"] = score(rows)
    record["per_question"] = rows
    path = save_result(record)
    run_id = log_record(record, path, ablation=args.ablation)  # MLflow (D-036)

    summary = record["overall"]
    print(f"\n{args.config_id} abstention on {args.split} ({config.LLM_MODEL})")
    print(f"accuracy {summary['accuracy']} over n={summary['n']}")
    print(
        f"answered although it should refuse: {summary['false_answer']}/{summary['unanswerable_n']}"
    )
    print(
        f"refused although it should answer:  {summary['false_refusal']}/{summary['answerable_n']}"
    )
    print(f"saved {path}")
    print(f"logged to MLflow: run {run_id} (open with: mlflow ui)")


if __name__ == "__main__":
    main()

"""Generation eval (step 3.9, D-014): is the final ANSWER good, not just the search?

Run: python -m evals.run_generation_eval --retrieval best --n 20 --config-id G-best
For the first N answerable dev questions + every unanswerable one:
1. retrieve chunks (best = hybrid + MiniLM rerank; dense = the Phase 1/2 app),
2. the generator LLM answers (the app's prompt, rag.generate),
3. a DIFFERENT judge LLM scores faithfulness, correctness and relevancy (judge_prompts.py),
4. abstention is checked with plain code (the exact "not found" sentence).
Every LLM output is cached in evals/cache/, so a re-run is free and gives the same numbers.
About 20% of judged items go to evals/spot_checks/ for a human to agree or disagree.
"""

import argparse
import hashlib
import json
import random
import time

from openai import RateLimitError

from docpilot import config
from docpilot.llm.client import chat, get_llm_client
from docpilot.rag import build_context, generate
from docpilot.retrieval.pipeline import BEST, DENSE_ONLY, retrieve
from docpilot.store.qdrant_store import get_client
from evals.common import base_record, load_split, save_result
from evals.judge_prompts import JUDGE_PROMPT, JUDGE_SYSTEM, JUDGE_VERSION, parse_judge
from evals.metrics import mean, percentile
from evals.run_abstention_check import said_not_found
from evals.tracking import log_record
from evals.transform_cache import CACHE_DIR

# Different family from the generator (gpt-oss), so the judge does not grade its own style
# (Rule 11). Checked on GET /openai/v1/models with the learner's key, 2026-10-22.
DEFAULT_JUDGE = "qwen/qwen3.8-27b"
SETTINGS = {"best": BEST, "dense": DENSE_ONLY}
SPOT_CHECK_SHARE = 0.2
MAX_ATTEMPTS = 5


def with_retries(function, *args):
    """Run function(*args); on a 429 (free-tier rate limit) wait and try again."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return function(*args)
        except RateLimitError as error:
            if attempt == MAX_ATTEMPTS:
                raise
            wait = float(error.response.headers.get("retry-after", 15 * attempt))
            print(f"  429 rate limit, waiting {wait:.0f} s (attempt {attempt})")
            time.sleep(wait)
    raise AssertionError("unreachable")


def load_cache(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_cache(path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def safe(name: str) -> str:
    return name.replace("/", "_")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generation eval with an LLM judge.")
    parser.add_argument("--retrieval", default="best", choices=sorted(SETTINGS))
    parser.add_argument("--n", type=int, default=20, help="answerable dev questions to use")
    parser.add_argument("--judge", default=DEFAULT_JUDGE)
    parser.add_argument("--config-id", default="G-best")
    parser.add_argument("--ablation", action="store_true")
    args = parser.parse_args()

    dev = load_split("dev")
    answerable = [item for item in dev if item["should_answer"]][: args.n]
    items = answerable + [item for item in dev if not item["should_answer"]]
    settings = SETTINGS[args.retrieval]
    gen_path = CACHE_DIR / f"generation_{args.retrieval}_{safe(config.LLM_MODEL)}.json"
    judge_path = CACHE_DIR / f"judge_{safe(args.judge)}_{JUDGE_VERSION}.json"
    answers, judgements = load_cache(gen_path), load_cache(judge_path)
    llm = get_llm_client()

    client = get_client()
    rows = []
    try:
        for number, item in enumerate(items, start=1):
            question = item["question"]
            hits = retrieve(question, client, settings)
            context = build_context(hits)
            if question not in answers:  # one paid generator call per question, ever
                start = time.perf_counter()
                answer = with_retries(generate, question, hits, llm)
                llm_ms = round((time.perf_counter() - start) * 1000, 1)
                answers[question] = {"answer": answer, "llm_ms": llm_ms}
                save_cache(gen_path, answers)
            answer = answers[question]["answer"]
            abstained = said_not_found(answer)
            row = {
                "id": item["id"],
                "type": item["type"],
                "should_answer": item["should_answer"],
                "abstained": abstained,
                "abstention_correct": abstained != item["should_answer"],
                "answer": answer,
                "llm_ms": answers[question]["llm_ms"],
                "sources": [f"{h['source']}#{h['chunk_number']}" for h in hits],
            }
            # Judge only real answers to answerable questions; a refusal has no claims.
            if item["should_answer"] and not abstained:
                key = hashlib.sha256(f"{question}\n{context}\n{answer}".encode()).hexdigest()
                if key not in judgements:
                    prompt = JUDGE_PROMPT.format(
                        context=context,
                        question=question,
                        reference=item["reference_answer"],
                        answer=answer,
                    )
                    reply = with_retries(chat, llm, JUDGE_SYSTEM, prompt, args.judge)
                    judgements[key] = parse_judge(reply)
                    save_cache(judge_path, judgements)
                row.update(judgements[key])
            rows.append(row)
            print(f"{number}/{len(items)} {item['id']} abstained={abstained}", end="")
            print(f" faithfulness={row.get('faithfulness')} correctness={row.get('correctness')}")
    finally:
        client.close()

    judged = [row for row in rows if "faithfulness" in row]
    faithful = [row["faithfulness"] for row in judged if row["faithfulness"] is not None]
    unanswerable = [row for row in rows if not row["should_answer"]]
    answerable_rows = [row for row in rows if row["should_answer"]]
    record = base_record(args.config_id, "dev", "generation", settings.collection)
    record["settings"].update(
        {
            "retrieval": args.retrieval,
            "retrieval_settings": str(settings),
            "generator": config.LLM_MODEL,
            "judge": args.judge,
            "judge_version": JUDGE_VERSION,
            "n_answerable": len(answerable),
        }
    )
    record["overall"] = {
        "n": len(rows),
        "n_judged": len(judged),
        "faithfulness": round(mean(faithful), 3),
        # Share of judged answers with at least one claim the context does not support.
        "hallucination_rate": round(mean([float(f < 1.0) for f in faithful]), 3),
        "correctness": round(mean([row["correctness_score"] for row in judged]), 3),
        "relevancy": round(mean([row["relevancy"] for row in judged]), 2),
        "abstention_accuracy": round(mean([row["abstention_correct"] for row in rows]), 3),
        "false_refusals": sum(row["abstained"] for row in answerable_rows),
        "missed_refusals": sum(not row["abstained"] for row in unanswerable),
        "llm_p50_ms": percentile([row["llm_ms"] for row in rows], 50),
        "llm_p95_ms": percentile([row["llm_ms"] for row in rows], 95),
    }
    record["per_question"] = rows
    path = save_result(record)
    write_spot_checks(path.stem, judged)
    run_id = log_record(record, path, ablation=args.ablation)
    print(f"\n{args.config_id} ({record['git_commit']}): {json.dumps(record['overall'])}")
    print(f"saved {path}; MLflow run {run_id}")


def write_spot_checks(run_name: str, judged: list[dict]) -> None:
    """About 20% of judged answers, for a human to check the judge (Rule 11)."""
    sample = random.Random(42).sample(judged, max(1, round(len(judged) * SPOT_CHECK_SHARE)))
    lines = [f"# Spot check: {run_name}", "", "For each item: do you agree with the judge?", ""]
    for row in sample:
        lines += [
            f"## {row['id']} ({row['type']})",
            "",
            f"**Answer:** {row['answer']}",
            "",
            f"**Judge:** faithfulness {row['faithfulness']}, correctness {row['correctness']}"
            f" ({row['correctness_reason']}), relevancy {row['relevancy']}",
            f"**Unsupported claims (judge):** {row['unsupported_claims'] or 'none'}",
            "",
            "**Your verdict (agree / disagree, why):** ",
            "",
        ]
    folder = config.PROJECT_ROOT / "evals" / "spot_checks"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{run_name}.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()

"""How many LLM tokens does one answer use? (Phase 7 A2, D-063)

Groq's free plan limits TOKENS too (sample limits on 2026-10-23: 8K per minute, 200K per
day for gpt-oss-120b), so the site's daily question cap must come from a real token count,
not a guess. This sends N dev-set questions through the same retrieval and guarded
prompts as the chat app and prints what Groq reports in `usage`.

Run: python -m scripts.measure_tokens            (5 questions; -m so `evals` imports)
     python -m scripts.measure_tokens --n 10
Cost: N real Groq calls (free plan). Needs Qdrant running and GROQ_API_KEY in .env.
"""

import argparse
import sys

from docpilot import config
from docpilot.llm.client import get_llm_client
from docpilot.rag import prompts
from docpilot.retrieval.pipeline import BEST, retrieve
from docpilot.store.qdrant_store import get_client
from evals.common import load_split


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Measure LLM tokens per answer.")
    parser.add_argument("--n", type=int, default=5, help="how many dev questions")
    args = parser.parse_args()

    # Answerable questions only: a refused question costs no answer call.
    questions = [item["question"] for item in load_split("dev") if item["should_answer"]]
    qdrant, llm = get_client(), get_llm_client()
    totals = []
    try:
        print(f"model: {config.LLM_MODEL}")
        print(f"{'prompt':>7} {'answer':>7} {'total':>7}  question")
        for question in questions[: args.n]:
            hits = retrieve(question, qdrant, BEST, {})
            system, user = prompts(question, hits, guarded=True)
            response = llm.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0,
            )
            # completion_tokens includes the model's hidden reasoning (gpt-oss "thinks").
            usage = response.usage
            totals.append(usage.total_tokens)
            print(
                f"{usage.prompt_tokens:>7} {usage.completion_tokens:>7} {usage.total_tokens:>7}"
                f"  {question[:60]}"
            )
    finally:
        qdrant.close()

    totals.sort()
    print(f"\nn={len(totals)}  median total={totals[len(totals) // 2]}  max={totals[-1]}")


if __name__ == "__main__":
    main()

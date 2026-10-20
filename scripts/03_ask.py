"""Ask DocPilot one question from the command line and see what was retrieved.

Run: python scripts/03_ask.py "How do I make a query parameter optional?"
     python scripts/03_ask.py --full "..."   (print whole chunks, not a preview)
"""

import argparse
import sys

from docpilot import config
from docpilot.llm.client import get_llm_client
from docpilot.rag import ask
from docpilot.store.qdrant_store import get_client

PREVIEW_CHARS = 200


def main() -> None:
    # Windows uses cp1252 when output goes to a file (`> out.txt`); docs contain emoji and
    # LLM answers contain characters like U+202F, so printing crashed. Force UTF-8.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Ask a question about the indexed docs.")
    parser.add_argument("question", help="the question, in quotes")
    # Step 1b: a 200-char preview is not enough to judge "is the right chunk here?"
    parser.add_argument("--full", action="store_true", help="print whole chunk texts")
    args = parser.parse_args()
    question = args.question

    client = get_client(config.QDRANT_PATH)
    try:
        if not client.collection_exists(config.COLLECTION_NAME):
            sys.exit(f"No index found. Build it first:\n  {config.INGEST_COMMAND}")
        result = ask(question, client, get_llm_client())
    finally:
        client.close()

    print(f"\nQ: {question}\n")
    print(f"A: {result['answer']}\n")
    print("Sources (number = citation):")
    for number, hit in enumerate(result["sources"], start=1):
        print(f"[{number}] {hit['source']} #{hit['chunk_number']}  score {hit['score']:.3f}")
        if args.full:
            print(hit["text"] + "\n" + "-" * 60)
        else:
            preview = hit["text"][:PREVIEW_CHARS].replace("\n", " ")  # one line per source
            print(f"    {preview}...")

    # One question = one warm-or-cold sample, not a p50/p95 (D-031): the first stage
    # here includes loading the embedding model, so embed_query is a COLD number.
    timings = "  ".join(f"{stage} {ms} ms" for stage, ms in result["timings_ms"].items())
    print(f"\nTimings (1 run, cold start, {config.LLM_MODEL}): {timings}")


if __name__ == "__main__":
    main()

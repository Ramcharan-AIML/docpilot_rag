"""Ask DocPilot one question from the command line and see what was retrieved.

Run: python scripts/03_ask.py "How do I make a query parameter optional?"
"""

import argparse
import sys

from docpilot import config
from docpilot.llm import get_llm_client
from docpilot.rag import ask
from docpilot.vector_store import get_client

PREVIEW_CHARS = 200


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a question about the indexed docs.")
    parser.add_argument("question", help="the question, in quotes")
    question = parser.parse_args().question

    client = get_client(config.QDRANT_PATH)
    try:
        if not client.collection_exists(config.COLLECTION_NAME):
            sys.exit("No index found. Run scripts/02_ingest.py first.")
        result = ask(question, client, get_llm_client())
    finally:
        client.close()

    print(f"\nQ: {question}\n")
    print(f"A: {result['answer']}\n")
    print("Sources (number = citation):")
    for number, hit in enumerate(result["sources"], start=1):
        preview = hit["text"][:PREVIEW_CHARS].replace("\n", " ")  # one line per source
        print(f"[{number}] {hit['source']} #{hit['chunk_number']}  score {hit['score']:.3f}")
        print(f"    {preview}...")

    # One question = one warm-or-cold sample, not a p50/p95 (D-031): the first stage
    # here includes loading the embedding model, so embed_query is a COLD number.
    timings = "  ".join(f"{stage} {ms} ms" for stage, ms in result["timings_ms"].items())
    print(f"\nTimings (1 run, cold start, {config.LLM_MODEL}): {timings}")


if __name__ == "__main__":
    main()

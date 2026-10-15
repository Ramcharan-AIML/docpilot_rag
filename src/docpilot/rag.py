"""The naive RAG pipeline: embed question, search, build prompt, ask the LLM."""

import time

from openai import OpenAI
from qdrant_client import QdrantClient

from docpilot import config
from docpilot.embedding.dense import embed_query
from docpilot.llm.client import chat
from docpilot.store.qdrant_store import search

# D-008: this prompt is our first (weak) guardrail. A chunk that says "ignore the rules"
# can still fool it; real guards come in Phase 6.
SYSTEM_PROMPT = f"""You answer questions about technical documentation.
Use ONLY the numbered context. Cite every fact with its number, like [1] or [2].

If the context does not contain the answer, reply exactly:
{config.NOT_FOUND_PHRASE}"""


def build_context(hits: list[dict]) -> str:
    """Number each chunk so the model can cite it: [1] (source: ...) text ...

    The numbers follow the order of `hits`, so citation [2] always means hits[1].
    """
    parts = []
    for number, hit in enumerate(hits, start=1):
        parts.append(f"[{number}] (source: {hit['source']})\n{hit['text']}")
    return "\n\n".join(parts)


def elapsed_ms(start: float) -> float:
    """Milliseconds since `start` (a time.perf_counter() reading), rounded for printing."""
    return round((time.perf_counter() - start) * 1000, 1)


def ask(question: str, qdrant_client: QdrantClient, llm_client: OpenAI) -> dict:
    """Answer `question` from the indexed docs.

    Returns {"answer": str, "sources": hits, "timings_ms": {stage: ms}}. Timing every stage
    tells us WHERE the time goes, not just how much (D-031, primer_latency.md).
    """
    timings: dict[str, float] = {}
    total_start = time.perf_counter()

    start = time.perf_counter()
    query_vector = embed_query(question)
    timings["embed_query"] = elapsed_ms(start)

    start = time.perf_counter()
    hits = search(qdrant_client, config.COLLECTION_NAME, query_vector, config.TOP_K)
    timings["search"] = elapsed_ms(start)

    if not hits:
        # Empty index: nothing to ground an answer on, so do not spend an LLM call.
        timings["total"] = elapsed_ms(total_start)
        return {"answer": config.NOT_FOUND_PHRASE, "sources": [], "timings_ms": timings}

    user_prompt = f"Context:\n{build_context(hits)}\n\nQuestion: {question}"
    start = time.perf_counter()
    answer = chat(llm_client, SYSTEM_PROMPT, user_prompt)
    timings["llm"] = elapsed_ms(start)

    timings["total"] = elapsed_ms(total_start)
    return {"answer": answer, "sources": hits, "timings_ms": timings}

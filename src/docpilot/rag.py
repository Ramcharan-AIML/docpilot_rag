"""The RAG pipeline: retrieve chunks, build prompt, ask the LLM.

Since step 3.10, retrieval goes through retrieval/pipeline.py: Qdrant hybrid search +
MiniLM reranker (the Phase 3 winners), the same code the evals measure.
"""

import time
from dataclasses import replace

from openai import OpenAI
from qdrant_client import QdrantClient

from docpilot import config
from docpilot.llm.client import chat
from docpilot.retrieval.pipeline import BEST, RetrievalSettings, retrieve

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


def ask(
    question: str,
    qdrant_client: QdrantClient,
    llm_client: OpenAI,
    collection: str = config.COLLECTION_NAME,
    settings: RetrievalSettings = BEST,
) -> dict:
    """Answer `question` from the indexed docs in `collection`.

    `collection` lets the evals measure latency and abstention for any chunking strategy
    (step 2.6); the API keeps the default from config.py. `settings` picks the retrieval
    (default: the Phase 3 winner; DENSE_ONLY = the Phase 1/2 app).

    Returns {"answer": str, "sources": hits, "timings_ms": {stage: ms}}. Timing every stage
    tells us WHERE the time goes, not just how much (D-031, primer_latency.md).
    """
    timings: dict[str, float] = {}
    total_start = time.perf_counter()

    # Fills timings with embed_query, search and (with the reranker) rerank.
    settings = replace(settings, collection=collection)
    hits = retrieve(question, qdrant_client, settings, timings)

    if not hits:
        # Empty index: nothing to ground an answer on, so do not spend an LLM call.
        timings["total"] = elapsed_ms(total_start)
        return {"answer": config.NOT_FOUND_PHRASE, "sources": [], "timings_ms": timings}

    start = time.perf_counter()
    answer = generate(question, hits, llm_client)
    timings["llm"] = elapsed_ms(start)

    timings["total"] = elapsed_ms(total_start)
    return {"answer": answer, "sources": hits, "timings_ms": timings}


def generate(question: str, hits: list[dict], llm_client: OpenAI) -> str:
    """The generation half of RAG: numbered context + question -> cited answer.

    Separate from retrieval so the generation eval (step 3.9) can feed it any hits.
    """
    user_prompt = f"Context:\n{build_context(hits)}\n\nQuestion: {question}"
    return chat(llm_client, SYSTEM_PROMPT, user_prompt)

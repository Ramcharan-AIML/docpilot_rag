"""The naive RAG pipeline: embed question, search, build prompt, ask the LLM."""

from openai import OpenAI
from qdrant_client import QdrantClient

from docpilot import config
from docpilot.embedder import embed_query
from docpilot.llm import chat
from docpilot.vector_store import search

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


def ask(question: str, qdrant_client: QdrantClient, llm_client: OpenAI) -> dict:
    """Answer `question` from the indexed docs. Returns {"answer": str, "sources": hits}."""
    query_vector = embed_query(question)
    hits = search(qdrant_client, config.COLLECTION_NAME, query_vector, config.TOP_K)
    if not hits:
        # Empty index: nothing to ground an answer on, so do not spend an LLM call.
        return {"answer": config.NOT_FOUND_PHRASE, "sources": []}

    user_prompt = f"Context:\n{build_context(hits)}\n\nQuestion: {question}"
    answer = chat(llm_client, SYSTEM_PROMPT, user_prompt)
    return {"answer": answer, "sources": hits}

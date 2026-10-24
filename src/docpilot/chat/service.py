"""One chat turn, end to end (D-061). Yields events the API streams to the browser.

message -> input guard -> memory (condense) -> input guard again -> retrieval (this chat's
files, or the main library) -> streamed LLM answer -> output guard on the FULL answer ->
saved in the chat.

Events (dicts, sent as Server-Sent Events by chat_api.py):
  {"type": "sources", "sources": [...], "question": standalone question}
  {"type": "token", "text": "..."}                 many, while the LLM writes
  {"type": "done", "answer", "status", "sources", "timings"}   always last

Streaming and the output guard: the guard needs the whole answer, so it runs at the end.
If it rejects the answer, "done" carries the replacement and the UI swaps the text. The
user may glimpse a rejected draft for a second; that is the usual trade-off for streaming
(ChatGPT also retracts some answers after streaming them).
"""

import time
from collections.abc import Iterator
from dataclasses import replace

from openai import OpenAI
from qdrant_client import QdrantClient

from docpilot import config
from docpilot.chat import store
from docpilot.chat.memory import answer_about_chat, condense
from docpilot.guardrails.input_guard import check_input
from docpilot.guardrails.output_guard import CANARY, check_output, redact_secrets
from docpilot.llm.client import chat_stream
from docpilot.rag import elapsed_ms, prompts
from docpilot.retrieval.pipeline import BEST, retrieve

# D-066: what the user reads when nothing matches. The answer still STARTS with
# NOT_FOUND_PHRASE (the prompts and the output guard use that exact sentence).
LIBRARY_HINT = (
    " The demo library covers FastAPI, Pydantic, Docker and RAG / LLM papers. To ask about"
    " something else, attach your own PDF, Markdown or text file (the paperclip)."
)
FILES_HINT = " I searched only the files in this chat."
NO_LIBRARY = (
    "The demo library is switched off and this chat has no files yet. Attach a PDF, Markdown"
    " or text file (the paperclip), or switch the demo library on."
)
STILL_INDEXING = "Your file is still being prepared. Ask again when it shows a green tick."


def pick_library(chat_id: str, library: str | None) -> str:
    """Where this turn searches (D-066): "files", "main" or "off".

    The lock: once a chat has uploaded files (not failed ones), it searches ONLY them, so
    an answer never mixes a personal file with the demo library. A new chat starts with
    the library again. Without files, the toggle decides: "off" = nothing to search.
    """
    if any(f["status"] != "failed" for f in store.list_files(chat_id)):
        return "files"
    return "off" if library == "off" else "main"


def public_source(hit: dict) -> dict:
    """What the browser may see about a chunk: never the chunk text itself."""
    return {
        "source": hit["source"],
        "name": hit["source"].rsplit("/", 1)[-1],
        "chunk_number": hit.get("chunk_number", 0),
        "section": " > ".join(hit.get("heading_path") or []),
        "score": round(float(hit.get("score", 0.0)), 4),
    }


def finish(chat_id: str, answer: str, status: str, sources: list, timings: dict) -> dict:
    store.add_message(chat_id, "assistant", answer, status, sources, timings)
    return {
        "type": "done",
        "answer": answer,
        "status": status,
        "sources": sources,
        "timings": timings,
    }


def run_turn(
    chat_id: str,
    message: str,
    qdrant_client: QdrantClient,
    llm_client: OpenAI,
    library: str | None = None,
) -> Iterator[dict]:
    timings: dict[str, float] = {}
    total = time.perf_counter()
    history = store.get_messages(chat_id)  # read BEFORE saving the new message
    store.add_message(chat_id, "user", message)

    start = time.perf_counter()
    verdict = check_input(message)
    timings["input_guard"] = elapsed_ms(start)
    if not verdict.allowed:
        timings["total"] = elapsed_ms(total)
        yield finish(chat_id, config.BLOCKED_PHRASE, "blocked_input", [], timings)
        return

    # Before any LLM call: nothing to search = a clear instruction, not a wasted Groq call.
    where = pick_library(chat_id, library)
    if where == "off":
        yield finish(chat_id, NO_LIBRARY, "no_library", [], timings)
        return
    if where == "files" and not any(f["status"] == "ready" for f in store.list_files(chat_id)):
        yield finish(chat_id, STILL_INDEXING, "indexing", [], timings)
        return
    hint = FILES_HINT if where == "files" else LIBRARY_HINT

    start = time.perf_counter()
    question, about_chat = condense(verdict.text, history, llm_client)
    if history:
        timings["condense"] = elapsed_ms(start)

    if about_chat:
        # "What was my last question?": answered from the history, not the documents.
        start = time.perf_counter()
        answer, _ = redact_secrets(answer_about_chat(question, history, llm_client))
        timings["llm"] = elapsed_ms(start)
        timings["total"] = elapsed_ms(total)
        if CANARY in answer:
            yield finish(chat_id, config.BLOCKED_PHRASE, "blocked_output", [], timings)
            return
        yield {"type": "token", "text": answer}
        yield finish(chat_id, answer, "chat", [], timings)
        return

    # The rewritten question is new text: check it too (cheap, and it could carry an
    # attack hidden in earlier turns).
    if question != verdict.text and not check_input(question).allowed:
        timings["total"] = elapsed_ms(total)
        yield finish(chat_id, config.BLOCKED_PHRASE, "blocked_input", [], timings)
        return

    if where == "files":
        settings = replace(BEST, collection=config.UPLOADS_COLLECTION, chat_id=chat_id)
    else:
        settings = BEST
    hits = retrieve(question, qdrant_client, settings, timings)
    sources = [public_source(hit) for hit in hits]
    yield {"type": "sources", "sources": sources, "question": question}
    if not hits:
        timings["total"] = elapsed_ms(total)
        yield finish(chat_id, config.NOT_FOUND_PHRASE + hint, "not_found", [], timings)
        return

    system, user = prompts(question, hits, guarded=True)
    start = time.perf_counter()
    parts: list[str] = []
    for piece in chat_stream(llm_client, system, user):
        if not parts:
            timings["first_token"] = elapsed_ms(start)  # what the user feels as "speed"
        parts.append(piece)
        yield {"type": "token", "text": piece}
    timings["llm"] = elapsed_ms(start)

    start = time.perf_counter()
    verdict = check_output("".join(parts), len(hits))
    timings["output_guard"] = elapsed_ms(start)
    timings["total"] = elapsed_ms(total)
    if not verdict.allowed:
        yield finish(chat_id, verdict.text, "blocked_output", [], timings)
    elif verdict.reason == "not_found":
        yield finish(chat_id, verdict.text + hint, "not_found", [], timings)
    else:
        yield finish(chat_id, verdict.text, "ok", sources, timings)

"""Mini API for Phase 1: the same ask() behind POST /ask. Becomes the api/ package in Phase 7.

Run: uvicorn docpilot.api:app --reload    then open http://127.0.0.1:8000/docs
Local-mode Qdrant allows ONE process (D-003): stop the API before running 02_ingest.py.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

from docpilot.guardrails.input_guard import MAX_QUESTION_CHARS
from docpilot.llm.client import get_llm_client
from docpilot.rag import ask
from docpilot.retrieval.pipeline import warm_up_models
from docpilot.store.qdrant_store import get_client


class AskRequest(BaseModel):
    # Pydantic rejects bad input with a 422 before our code runs: the first, cheapest wall.
    # The input guard (Phase 6) repeats the length check for callers that skip the API.
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)


class Source(BaseModel):
    # Only what a client needs to show a citation; the chunk text stays on the server.
    source: str
    chunk_number: int
    score: float


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    # Phase 6: "ok", "not_found", "blocked_input" or "blocked_output". WHICH rule fired is
    # logged on the server only: telling attackers the rule helps them get around it.
    status: str
    timings_ms: dict[str, float]  # per stage, for the UI and for Phase 7 metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once at startup: open Qdrant and the LLM client, keep them on app.state.

    Opening them per request would re-open the database folder and a new HTTPS
    connection every time; once at startup is what makes later requests "warm".
    """
    app.state.qdrant = get_client()
    app.state.llm = get_llm_client()
    # Step 3.10: load the 3 models now (BGE, BM25, MiniLM reranker), not on the first
    # question: otherwise the first user waits seconds for loading (a "cold start").
    warm_up_models()
    yield  # the app serves requests while we are paused here
    app.state.qdrant.close()  # runs once at shutdown (local mode: releases the folder lock)


app = FastAPI(title="DocPilot", lifespan=lifespan)


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(request: AskRequest) -> AskResponse:
    # A plain `def` (not async): FastAPI runs it in a thread pool, so the slow
    # model and LLM calls do not freeze the server. Async comes in Phase 7.
    result = ask(request.question, app.state.qdrant, app.state.llm)
    return AskResponse(
        answer=result["answer"],
        sources=result["sources"],
        status=result["status"],
        timings_ms=result["timings_ms"],
    )

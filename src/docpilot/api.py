"""DocPilot API: POST /ask (stateless, main library) + the chat API for the React UI.

Run: uvicorn docpilot.api:app --reload    then open http://127.0.0.1:8000/docs
Local-mode Qdrant allows ONE process (D-003): stop the API before running 02_ingest.py.

/ask            one question, no memory: scripts, evals, curl
/api/...        chats, files, streaming answers (chat_api.py, D-061)
/               the built React app (web/dist), when it exists
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from docpilot import config
from docpilot.chat import store
from docpilot.chat_api import router as chat_router
from docpilot.guardrails.input_guard import MAX_QUESTION_CHARS
from docpilot.llm.client import get_llm_client
from docpilot.rag import ask
from docpilot.retrieval.pipeline import warm_up_models
from docpilot.store.qdrant_store import get_client

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
WEB_DIST = config.PROJECT_ROOT / "web" / "dist"  # `npm run build` writes the React app here


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
    store.init_db()  # creates the chat tables on the first run (D-061)
    # Step 3.10: load the 3 models now (BGE, BM25, MiniLM reranker), not on the first
    # question: otherwise the first user waits seconds for loading (a "cold start").
    warm_up_models()
    yield  # the app serves requests while we are paused here
    app.state.qdrant.close()  # runs once at shutdown (local mode: releases the folder lock)


app = FastAPI(title="DocPilot", lifespan=lifespan)
app.include_router(chat_router)


@app.get("/health")
def health() -> dict:
    """Cheap "is the API up?" check (Docker and Prometheus use it in Phase 7)."""
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(request: AskRequest) -> AskResponse:
    # A plain `def` (not async): FastAPI runs it in a thread pool, so the slow
    # model and LLM calls do not freeze the server.
    if not app.state.qdrant.collection_exists(config.COLLECTION_NAME):
        raise HTTPException(status_code=503, detail="The main library is not indexed yet.")
    result = ask(request.question, app.state.qdrant, app.state.llm)
    return AskResponse(
        answer=result["answer"],
        sources=result["sources"],
        status=result["status"],
        timings_ms=result["timings_ms"],
    )


# Last, so /ask, /health and /api/... win: every other path serves the React app.
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")

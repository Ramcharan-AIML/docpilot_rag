"""Mini API for Phase 1: the same ask() behind POST /ask. Becomes the api/ package in Phase 7.

Run: uvicorn docpilot.api:app --reload    then open http://127.0.0.1:8000/docs
Local-mode Qdrant allows ONE process (D-003): stop the API before running 02_ingest.py.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

from docpilot import config
from docpilot.llm.client import get_llm_client
from docpilot.rag import ask
from docpilot.store.qdrant_store import get_client

MAX_QUESTION_CHARS = 2000  # a real question is far shorter; huge inputs waste LLM tokens


class AskRequest(BaseModel):
    # Pydantic rejects bad input with a 422 before our code runs.
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)


class Source(BaseModel):
    # Only what a client needs to show a citation; the chunk text stays on the server.
    source: str
    chunk_number: int
    score: float


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once at startup: open Qdrant and the LLM client, keep them on app.state.

    Opening them per request would re-open the database folder and a new HTTPS
    connection every time; once at startup is what makes later requests "warm".
    """
    app.state.qdrant = get_client(config.QDRANT_PATH)
    app.state.llm = get_llm_client()
    yield  # the app serves requests while we are paused here
    app.state.qdrant.close()  # runs once at shutdown: releases the folder lock


app = FastAPI(title="DocPilot", lifespan=lifespan)


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(request: AskRequest) -> AskResponse:
    # A plain `def` (not async): FastAPI runs it in a thread pool, so the slow
    # model and LLM calls do not freeze the server. Async comes in Phase 7.
    result = ask(request.question, app.state.qdrant, app.state.llm)
    return AskResponse(answer=result["answer"], sources=result["sources"])

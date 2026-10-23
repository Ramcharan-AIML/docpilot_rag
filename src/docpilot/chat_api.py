"""Chat endpoints for the React UI (D-061), mounted under /api by api.py.

POST   /api/chats                          new chat
GET    /api/chats                          all chats, newest first (the sidebar)
GET    /api/chats/{id}                     one chat: messages + files
PATCH  /api/chats/{id}                     rename
DELETE /api/chats/{id}                     delete chat, its files and their vectors
POST   /api/chats/{id}/files               upload; returns at once ("processing")
GET    /api/chats/{id}/files               file chips; the UI polls until "ready"
DELETE /api/chats/{id}/files/{file_id}     remove one file and its vectors
POST   /api/chats/{id}/messages            ask; the answer STREAMS back (Server-Sent Events)

Privacy (A1, D-063): every chat call needs the header X-Visitor-Id (a random id the
browser makes once). A visitor sees only their own chats; anyone else's chat is a 404, as
if it did not exist. This is privacy, not security: there is no password.
"""

import json
import logging
import re
import shutil
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from openai import RateLimitError
from pydantic import BaseModel, Field

from docpilot import config, limits
from docpilot.chat import jobs, store
from docpilot.chat.service import run_turn
from docpilot.guardrails.input_guard import MAX_QUESTION_CHARS
from docpilot.ingestion.uploads import UploadError, save_upload
from docpilot.store.qdrant_store import delete_source, delete_where

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


class MessageRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    library: str | None = Field(default=None, pattern="^(files|main)$")  # None = automatic


class RenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=store.TITLE_CHARS)


# A browser UUID is 36 characters ("3f9c...-...-e1"). Allow 16-64 letters, digits and "-"
# so a stray value (empty, a huge string, SQL) is refused before it touches the database.
VISITOR_ID = re.compile(r"^[A-Za-z0-9-]{16,64}$")


def visitor(x_visitor_id: Annotated[str, Header()] = "") -> str:
    """FastAPI reads the X-Visitor-Id header into x_visitor_id (it maps _ to -)."""
    if not VISITOR_ID.fullmatch(x_visitor_id):
        raise HTTPException(status_code=400, detail="Missing or bad visitor id.")
    return x_visitor_id


Visitor = Annotated[str, Depends(visitor)]


def client_ip(request: Request) -> str:
    """The caller's address. Behind Caddy this is Caddy's address unless uvicorn trusts the
    proxy's X-Forwarded-For header (--proxy-headers, set in Stage B)."""
    return request.client.host if request.client else "unknown"


def refuse_if_limited(message: str | None) -> None:
    """429 Too Many Requests: the standard code for "slow down"; the UI shows the text."""
    if message:
        raise HTTPException(status_code=429, detail=message)


def existing_chat(chat_id: str, owner: str) -> dict:
    """404 for a chat that does not exist AND for someone else's chat: a stranger cannot
    even learn that the chat exists (a 403 would tell them)."""
    chat = store.get_chat(chat_id)
    if chat is None or chat["owner"] != owner:
        raise HTTPException(status_code=404, detail="Chat not found.")
    return chat


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/chats")
def new_chat(owner: Visitor) -> dict:
    return store.create_chat(owner)


@router.get("/chats")
def all_chats(owner: Visitor) -> list[dict]:
    return store.list_chats(owner)


@router.get("/chats/{chat_id}")
def one_chat(chat_id: str, owner: Visitor) -> dict:
    chat = existing_chat(chat_id, owner)
    return {**chat, "messages": store.get_messages(chat_id), "files": store.list_files(chat_id)}


@router.patch("/chats/{chat_id}")
def rename(chat_id: str, body: RenameRequest, owner: Visitor) -> dict:
    existing_chat(chat_id, owner)
    store.rename_chat(chat_id, body.title)
    return store.get_chat(chat_id)


@router.delete("/chats/{chat_id}")
def remove_chat(chat_id: str, request: Request, owner: Visitor) -> dict:
    existing_chat(chat_id, owner)
    delete_where(request.app.state.qdrant, config.UPLOADS_COLLECTION, "chat_id", chat_id)
    shutil.rmtree(config.UPLOADS_DIR / chat_id, ignore_errors=True)
    store.delete_chat(chat_id)
    return {"deleted": chat_id}


@router.post("/chats/{chat_id}/files", status_code=202)
def upload(chat_id: str, file: UploadFile, request: Request, owner: Visitor) -> dict:
    """202 Accepted: the file is saved and checked now, indexed in the background."""
    existing_chat(chat_id, owner)
    if len(store.list_files(chat_id)) >= config.MAX_FILES_PER_CHAT:
        detail = f"This chat already has {config.MAX_FILES_PER_CHAT} files (the limit)."
        raise HTTPException(status_code=400, detail=detail)
    refuse_if_limited(limits.upload_refusal(client_ip(request)))
    try:
        path, name, source, pages = save_upload(file.filename or "", file.file.read(), chat_id)
    except UploadError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    row = store.add_file(chat_id, name, source, pages)
    jobs.submit(row, path, request.app.state.qdrant)
    return row


@router.get("/chats/{chat_id}/files")
def files(chat_id: str, owner: Visitor) -> list[dict]:
    existing_chat(chat_id, owner)
    return store.list_files(chat_id)


@router.delete("/chats/{chat_id}/files/{file_id}")
def remove_file(chat_id: str, file_id: str, request: Request, owner: Visitor) -> dict:
    existing_chat(chat_id, owner)
    file = store.get_file(file_id)
    if file is None or file["chat_id"] != chat_id:
        raise HTTPException(status_code=404, detail="File not found.")
    delete_source(request.app.state.qdrant, config.UPLOADS_COLLECTION, file["source"])
    (config.UPLOADS_DIR / chat_id / file["name"]).unlink(missing_ok=True)
    store.delete_file(file_id)
    return {"deleted": file_id}


@router.post("/chats/{chat_id}/messages")
def message(
    chat_id: str, body: MessageRequest, request: Request, owner: Visitor
) -> StreamingResponse:
    """Server-Sent Events: one "data: {json}" line per event, so text appears as it is
    written. Why SSE and not WebSockets: one direction (server -> browser) is all we need,
    and SSE is plain HTTP."""
    existing_chat(chat_id, owner)
    # Checked before the stream starts, so the refusal is a normal 429 response.
    refuse_if_limited(limits.question_refusal(owner, client_ip(request)))
    qdrant, llm = request.app.state.qdrant, request.app.state.llm

    def send(event: dict) -> str:
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    def events():
        # A3: wait for one of the 2 answer seats; tell the user why nothing happens yet.
        if not limits.take_answer_seat(0):
            yield send({"type": "stage", "text": "Waiting in line: DocPilot is busy"})
            if not limits.take_answer_seat(config.QUEUE_WAIT_SECONDS):
                yield send({"type": "error", "message": limits.BUSY})
                return
        try:
            for event in run_turn(chat_id, body.question, qdrant, llm, body.library):
                yield send(event)
        except RateLimitError:
            # A4: Groq still said 429 after the openai library's 2 retries. Not a bug: the
            # free quota is used up for this minute. A friendly message, not "went wrong".
            logger.warning("LLM rate limit (429) after retries")
            yield send({"type": "error", "message": limits.BUSY})
        except Exception:  # e.g. the LLM provider is down: tell the UI instead of hanging
            logger.exception("chat turn failed")
            yield send({"type": "error", "message": "Something went wrong. Please try again."})
        finally:
            limits.free_answer_seat()  # also runs when the user presses Stop

    return StreamingResponse(events(), media_type="text/event-stream")

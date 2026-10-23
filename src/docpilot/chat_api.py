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
"""

import json
import logging
import shutil

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from docpilot import config
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


def existing_chat(chat_id: str) -> dict:
    chat = store.get_chat(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found.")
    return chat


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/chats")
def new_chat() -> dict:
    return store.create_chat()


@router.get("/chats")
def all_chats() -> list[dict]:
    return store.list_chats()


@router.get("/chats/{chat_id}")
def one_chat(chat_id: str) -> dict:
    chat = existing_chat(chat_id)
    return {**chat, "messages": store.get_messages(chat_id), "files": store.list_files(chat_id)}


@router.patch("/chats/{chat_id}")
def rename(chat_id: str, body: RenameRequest) -> dict:
    existing_chat(chat_id)
    store.rename_chat(chat_id, body.title)
    return store.get_chat(chat_id)


@router.delete("/chats/{chat_id}")
def remove_chat(chat_id: str, request: Request) -> dict:
    existing_chat(chat_id)
    delete_where(request.app.state.qdrant, config.UPLOADS_COLLECTION, "chat_id", chat_id)
    shutil.rmtree(config.UPLOADS_DIR / chat_id, ignore_errors=True)
    store.delete_chat(chat_id)
    return {"deleted": chat_id}


@router.post("/chats/{chat_id}/files", status_code=202)
def upload(chat_id: str, file: UploadFile, request: Request) -> dict:
    """202 Accepted: the file is saved and checked now, indexed in the background."""
    existing_chat(chat_id)
    try:
        path, name, source, pages = save_upload(file.filename or "", file.file.read(), chat_id)
    except UploadError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    row = store.add_file(chat_id, name, source, pages)
    jobs.submit(row, path, request.app.state.qdrant)
    return row


@router.get("/chats/{chat_id}/files")
def files(chat_id: str) -> list[dict]:
    existing_chat(chat_id)
    return store.list_files(chat_id)


@router.delete("/chats/{chat_id}/files/{file_id}")
def remove_file(chat_id: str, file_id: str, request: Request) -> dict:
    file = store.get_file(file_id)
    if file is None or file["chat_id"] != chat_id:
        raise HTTPException(status_code=404, detail="File not found.")
    delete_source(request.app.state.qdrant, config.UPLOADS_COLLECTION, file["source"])
    (config.UPLOADS_DIR / chat_id / file["name"]).unlink(missing_ok=True)
    store.delete_file(file_id)
    return {"deleted": file_id}


@router.post("/chats/{chat_id}/messages")
def message(chat_id: str, body: MessageRequest, request: Request) -> StreamingResponse:
    """Server-Sent Events: one "data: {json}" line per event, so text appears as it is
    written. Why SSE and not WebSockets: one direction (server -> browser) is all we need,
    and SSE is plain HTTP."""
    existing_chat(chat_id)
    qdrant, llm = request.app.state.qdrant, request.app.state.llm

    def events():
        try:
            for event in run_turn(chat_id, body.question, qdrant, llm, body.library):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception:  # e.g. the LLM provider is down: tell the UI instead of hanging
            logger.exception("chat turn failed")
            error = {"type": "error", "message": "Something went wrong. Please try again."}
            yield f"data: {json.dumps(error)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")

"""Saved chats in SQLite (D-061): chats, their messages, their files.

Why SQLite: it is built into Python (no new dependency, no server), one file on disk, and
plenty for one user. Why not Postgres: a server to run for a laptop demo; it is the
Phase 7 upgrade when many users share one API.

Every function opens its own short connection: FastAPI runs requests in several threads,
and a sqlite3 connection must not be shared between threads.
"""

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from docpilot import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    owner TEXT NOT NULL DEFAULT ''   -- the visitor id that made it (A1, D-063)
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role TEXT NOT NULL,              -- "user" or "assistant"
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT '', -- assistant only: ok, not_found, blocked_input, ...
    sources TEXT NOT NULL DEFAULT '[]',
    timings TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    name TEXT NOT NULL,              -- what the user sees: "handbook.pdf"
    source TEXT NOT NULL,            -- what citations and Qdrant use: "uploads/<chat>/handbook.pdf"
    status TEXT NOT NULL,            -- processing, ready, failed
    pages INTEGER NOT NULL DEFAULT 0,
    chunks INTEGER NOT NULL DEFAULT 0,
    seconds REAL NOT NULL DEFAULT 0,
    error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""

NEW_CHAT_TITLE = "New chat"
TITLE_CHARS = 60


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or config.CHAT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row  # rows behave like dicts: row["title"]
    connection.execute("PRAGMA foreign_keys = ON")  # makes ON DELETE CASCADE work
    return connection


def init_db(path: Path | None = None) -> None:
    with closing(connect(path)) as db, db:
        db.executescript(SCHEMA)
        # Migration (A1): a database made before D-063 has no owner column. Old chats get
        # owner "" so no visitor sees them: privacy wins over convenience.
        columns = {row["name"] for row in db.execute("PRAGMA table_info(chats)")}
        if "owner" not in columns:
            db.execute("ALTER TABLE chats ADD COLUMN owner TEXT NOT NULL DEFAULT ''")
        db.execute("CREATE INDEX IF NOT EXISTS chats_owner ON chats(owner)")


def create_chat(owner: str = "", path: Path | None = None) -> dict:
    chat = {"id": uuid.uuid4().hex, "title": NEW_CHAT_TITLE, "created_at": now()}
    chat["updated_at"] = chat["created_at"]
    chat["owner"] = owner
    with closing(connect(path)) as db, db:  # `with db` = commit, or roll back on error
        db.execute(
            "INSERT INTO chats (id, title, created_at, updated_at, owner)"
            " VALUES (:id, :title, :created_at, :updated_at, :owner)",
            chat,
        )
    return chat


def list_chats(owner: str = "", path: Path | None = None) -> list[dict]:
    """One visitor's chats, newest activity first, like ChatGPT's sidebar."""
    with closing(connect(path)) as db:
        rows = db.execute(
            "SELECT * FROM chats WHERE owner = ? ORDER BY updated_at DESC, created_at DESC",
            (owner,),
        )
        return [dict(row) for row in rows]


def idle_chats(before: str, path: Path | None = None) -> list[str]:
    """Ids of chats with no activity since `before` (ISO time). The same ISO format with
    UTC everywhere means plain text order = time order."""
    with closing(connect(path)) as db:
        rows = db.execute("SELECT id FROM chats WHERE updated_at < ?", (before,))
        return [row["id"] for row in rows]


def get_chat(chat_id: str, path: Path | None = None) -> dict | None:
    with closing(connect(path)) as db:
        row = db.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
        return dict(row) if row else None


def rename_chat(chat_id: str, title: str, path: Path | None = None) -> None:
    with closing(connect(path)) as db, db:
        db.execute("UPDATE chats SET title = ? WHERE id = ?", (title[:TITLE_CHARS], chat_id))


def delete_chat(chat_id: str, path: Path | None = None) -> None:
    """Deletes its messages and file rows too (CASCADE). Vectors: see chat.jobs."""
    with closing(connect(path)) as db, db:
        db.execute("DELETE FROM chats WHERE id = ?", (chat_id,))


def add_message(
    chat_id: str,
    role: str,
    content: str,
    status: str = "",
    sources: list | None = None,
    timings: dict | None = None,
    path: Path | None = None,
) -> None:
    """Save one message; the first user message also becomes the chat's title."""
    stamp = now()
    with closing(connect(path)) as db, db:
        db.execute(
            "INSERT INTO messages (chat_id, role, content, status, sources, timings, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                chat_id,
                role,
                content,
                status,
                json.dumps(sources or []),
                json.dumps(timings or {}),
                stamp,
            ),
        )
        db.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (stamp, chat_id))
        if role == "user":
            title = " ".join(content.split())[:TITLE_CHARS]
            db.execute(
                "UPDATE chats SET title = ? WHERE id = ? AND title = ?",
                (title, chat_id, NEW_CHAT_TITLE),
            )


def get_messages(chat_id: str, path: Path | None = None) -> list[dict]:
    with closing(connect(path)) as db:
        rows = db.execute(
            "SELECT role, content, status, sources, timings, created_at FROM messages"
            " WHERE chat_id = ? ORDER BY id",
            (chat_id,),
        )
        return [
            {
                **dict(row),
                "sources": json.loads(row["sources"]),
                "timings": json.loads(row["timings"]),
            }
            for row in rows
        ]


def add_file(chat_id: str, name: str, source: str, pages: int, path: Path | None = None) -> dict:
    row = {
        "id": uuid.uuid4().hex,
        "chat_id": chat_id,
        "name": name,
        "source": source,
        "status": "processing",
        "pages": pages,
        "created_at": now(),
    }
    with closing(connect(path)) as db, db:
        db.execute(
            "INSERT INTO files (id, chat_id, name, source, status, pages, created_at)"
            " VALUES (:id, :chat_id, :name, :source, :status, :pages, :created_at)",
            row,
        )
    return get_file(row["id"], path)


def update_file(file_id: str, path: Path | None = None, **fields) -> None:
    """Set status / chunks / seconds / error when the background job finishes."""
    allowed = {"status", "chunks", "seconds", "error"}
    if not fields or set(fields) - allowed:
        raise ValueError(f"can only update {sorted(allowed)}")
    assignments = ", ".join(f"{name} = :{name}" for name in fields)
    with closing(connect(path)) as db, db:
        db.execute(f"UPDATE files SET {assignments} WHERE id = :id", {**fields, "id": file_id})


def get_file(file_id: str, path: Path | None = None) -> dict | None:
    with closing(connect(path)) as db:
        row = db.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
        return dict(row) if row else None


def list_files(chat_id: str, path: Path | None = None) -> list[dict]:
    with closing(connect(path)) as db:
        rows = db.execute("SELECT * FROM files WHERE chat_id = ? ORDER BY created_at", (chat_id,))
        return [dict(row) for row in rows]


def delete_file(file_id: str, path: Path | None = None) -> None:
    with closing(connect(path)) as db, db:
        db.execute("DELETE FROM files WHERE id = ?", (file_id,))

"""Tests for the A6 cleanup of idle chats, on a temp database and a fake Qdrant."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime

import pytest

from docpilot import config
from docpilot.chat import cleanup, store

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


class FakeQdrant:
    def __init__(self):
        self.deleted = []

    def collection_exists(self, name):
        return True

    def delete(self, collection_name, points_selector):
        self.deleted.append(points_selector.filter.must[0].match.value)


@pytest.fixture(autouse=True)
def temp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHAT_DB_PATH", tmp_path / "app.db")
    monkeypatch.setattr(config, "UPLOADS_DIR", tmp_path / "uploads")
    monkeypatch.setattr(config, "CHAT_IDLE_DAYS", 7)
    store.init_db()


def chat_last_used(when: str) -> str:
    chat = store.create_chat("visitor-a")
    with closing(sqlite3.connect(config.CHAT_DB_PATH)) as db, db:
        db.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (when, chat["id"]))
    return chat["id"]


def test_only_chats_idle_for_over_7_days_are_deleted_everywhere() -> None:
    old = chat_last_used("2026-10-20T12:00:00+00:00")  # 12 days before NOW
    recent = chat_last_used("2026-10-30T12:00:00+00:00")  # 2 days before NOW
    (config.UPLOADS_DIR / old).mkdir(parents=True)
    (config.UPLOADS_DIR / old / "notes.md").write_text("# old")
    qdrant = FakeQdrant()

    assert cleanup.cleanup_once(qdrant, now=NOW) == 1
    assert store.get_chat(old) is None  # rows
    assert not (config.UPLOADS_DIR / old).exists()  # uploaded files
    assert qdrant.deleted == [old]  # vectors
    assert store.get_chat(recent) is not None
    assert cleanup.cleanup_once(qdrant, now=NOW) == 0  # nothing left to do


def test_no_cleanup_thread_on_the_laptop(monkeypatch) -> None:
    monkeypatch.setattr(config, "PUBLIC_MODE", False)
    assert cleanup.start(FakeQdrant()) is None


def test_cleanup_thread_runs_and_stops(monkeypatch) -> None:
    monkeypatch.setattr(config, "PUBLIC_MODE", True)
    old = chat_last_used("2020-01-01T00:00:00+00:00")
    stop = cleanup.start(FakeQdrant())
    try:
        for _ in range(100):  # the first round runs at once; give it up to 1 s
            if store.get_chat(old) is None:
                break
            stop.wait(0.01)
        assert store.get_chat(old) is None
    finally:
        stop.set()

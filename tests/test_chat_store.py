"""Tests for the SQLite chat store, on a temp database file."""

import pytest

from docpilot import config
from docpilot.chat import store


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHAT_DB_PATH", tmp_path / "app.db")
    store.init_db()


def test_new_chat_is_listed_first() -> None:
    old = store.create_chat()
    new = store.create_chat()
    store.add_message(old["id"], "user", "hello")  # activity moves a chat to the top
    assert [chat["id"] for chat in store.list_chats()] == [old["id"], new["id"]]


def test_first_user_message_becomes_the_title() -> None:
    chat = store.create_chat()
    assert chat["title"] == "New chat"
    store.add_message(chat["id"], "user", "  How do   deploys work?  ")
    store.add_message(chat["id"], "user", "second question")  # does not rename again
    assert store.get_chat(chat["id"])["title"] == "How do deploys work?"


def test_messages_keep_order_sources_and_timings() -> None:
    chat = store.create_chat()
    store.add_message(chat["id"], "user", "q")
    sources = [{"source": "a.md", "chunk_number": 0}]
    store.add_message(chat["id"], "assistant", "a [1]", "ok", sources, {"llm": 900.0})
    messages = store.get_messages(chat["id"])
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[1]["sources"] == sources
    assert messages[1]["timings"] == {"llm": 900.0}
    assert messages[1]["status"] == "ok"


def test_files_lifecycle() -> None:
    chat = store.create_chat()
    file = store.add_file(chat["id"], "a.pdf", "uploads/x/a.pdf", pages=3)
    assert file["status"] == "processing"
    store.update_file(file["id"], status="ready", chunks=12, seconds=1.5)
    assert store.list_files(chat["id"])[0] | {"created_at": ""} == {
        **file,
        "status": "ready",
        "chunks": 12,
        "seconds": 1.5,
        "created_at": "",
    }
    with pytest.raises(ValueError):
        store.update_file(file["id"], name="evil")  # only status/chunks/seconds/error


def test_delete_chat_removes_its_messages_and_files() -> None:
    chat = store.create_chat()
    store.add_message(chat["id"], "user", "q")
    store.add_file(chat["id"], "a.pdf", "uploads/x/a.pdf", pages=1)
    store.delete_chat(chat["id"])
    assert store.get_chat(chat["id"]) is None
    assert store.get_messages(chat["id"]) == []
    assert store.list_files(chat["id"]) == []


def test_rename_is_cut_to_the_title_limit() -> None:
    chat = store.create_chat()
    store.rename_chat(chat["id"], "x" * 200)
    assert len(store.get_chat(chat["id"])["title"]) == store.TITLE_CHARS

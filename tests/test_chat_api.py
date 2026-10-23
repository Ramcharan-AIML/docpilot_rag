"""Tests for the chat endpoints. The chat turn and background indexing are fakes; the SQLite
store is real (temp file)."""

import json

import pytest
from fastapi.testclient import TestClient

from docpilot import api, chat_api, config
from docpilot.chat import store


class FakeQdrant:
    def __init__(self):
        self.deleted = []

    def collection_exists(self, name):
        return True

    def delete(self, collection_name, points_selector):
        self.deleted.append(points_selector.filter.must[0].match.value)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHAT_DB_PATH", tmp_path / "app.db")
    monkeypatch.setattr(config, "UPLOADS_DIR", tmp_path / "uploads")
    store.init_db()
    submitted = []
    monkeypatch.setattr(chat_api.jobs, "submit", lambda row, path, q: submitted.append(row))
    monkeypatch.setattr(api.app.state, "qdrant", FakeQdrant(), raising=False)
    monkeypatch.setattr(api.app.state, "llm", None, raising=False)
    test_client = TestClient(api.app)
    test_client.submitted = submitted
    return test_client


def test_chat_create_list_get_rename_delete(client) -> None:
    chat = client.post("/api/chats").json()
    assert client.get("/api/chats").json()[0]["id"] == chat["id"]
    assert client.get(f"/api/chats/{chat['id']}").json()["messages"] == []
    renamed = client.patch(f"/api/chats/{chat['id']}", json={"title": "Deploys"}).json()
    assert renamed["title"] == "Deploys"
    assert client.delete(f"/api/chats/{chat['id']}").status_code == 200
    assert client.get(f"/api/chats/{chat['id']}").status_code == 404
    assert api.app.state.qdrant.deleted == [chat["id"]]  # its vectors are removed too


def test_upload_returns_at_once_as_processing(client) -> None:
    chat = client.post("/api/chats").json()
    files = {"file": ("notes.md", b"# Notes\n\nHello", "text/markdown")}
    response = client.post(f"/api/chats/{chat['id']}/files", files=files)
    assert response.status_code == 202
    body = response.json()
    assert (body["name"], body["status"]) == ("notes.md", "processing")
    assert body["source"] == f"uploads/{chat['id']}/notes.md"
    assert client.submitted[0]["id"] == body["id"]  # handed to the background worker
    assert client.get(f"/api/chats/{chat['id']}/files").json()[0]["id"] == body["id"]


def test_bad_upload_is_refused_with_the_reason(client) -> None:
    chat = client.post("/api/chats").json()
    files = {"file": ("virus.exe", b"MZ", "application/octet-stream")}
    response = client.post(f"/api/chats/{chat['id']}/files", files=files)
    assert response.status_code == 400
    assert "Only PDF, Markdown" in response.json()["detail"]
    assert client.submitted == []


def test_delete_file(client) -> None:
    chat = client.post("/api/chats").json()
    files = {"file": ("notes.md", b"# N", "text/markdown")}
    file = client.post(f"/api/chats/{chat['id']}/files", files=files).json()
    assert client.delete(f"/api/chats/{chat['id']}/files/{file['id']}").status_code == 200
    assert client.get(f"/api/chats/{chat['id']}/files").json() == []
    assert client.delete(f"/api/chats/other/files/{file['id']}").status_code == 404


def test_message_streams_server_sent_events(client, monkeypatch) -> None:
    def fake_turn(chat_id, question, qdrant, llm, library):
        yield {"type": "token", "text": "Hi "}
        yield {"type": "done", "answer": "Hi [1]", "status": "ok", "sources": [], "timings": {}}

    monkeypatch.setattr(chat_api, "run_turn", fake_turn)
    chat = client.post("/api/chats").json()
    response = client.post(f"/api/chats/{chat['id']}/messages", json={"question": "hello"})
    assert response.headers["content-type"].startswith("text/event-stream")
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line]
    assert [event["type"] for event in events] == ["token", "done"]


def test_a_crash_becomes_an_error_event(client, monkeypatch) -> None:
    def broken_turn(*args):
        raise RuntimeError("provider down")
        yield  # makes this a generator

    monkeypatch.setattr(chat_api, "run_turn", broken_turn)
    chat = client.post("/api/chats").json()
    text = client.post(f"/api/chats/{chat['id']}/messages", json={"question": "q"}).text
    assert json.loads(text.strip()[6:])["type"] == "error"


def test_message_validation(client) -> None:
    chat = client.post("/api/chats").json()
    url = f"/api/chats/{chat['id']}/messages"
    assert client.post(url, json={"question": ""}).status_code == 422
    assert client.post(url, json={"question": "q", "library": "other"}).status_code == 422
    assert client.post("/api/chats/nope/messages", json={"question": "q"}).status_code == 404

"""Tests for the chat endpoints. The chat turn and background indexing are fakes; the SQLite
store is real (temp file)."""

import json
import threading

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import RateLimitError

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
    test_client = TestClient(api.app, headers={"X-Visitor-Id": VISITOR_A})
    test_client.submitted = submitted
    return test_client


VISITOR_A = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa"
OTHER = {"X-Visitor-Id": "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb"}  # visitor B


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


# --- A1: private chats per visitor ---


def test_visitor_b_cannot_see_or_touch_visitor_a_chat(client, monkeypatch) -> None:
    def fake_turn(*args):
        yield {"type": "done", "answer": "", "status": "ok", "sources": [], "timings": {}}

    monkeypatch.setattr(chat_api, "run_turn", fake_turn)
    chat = client.post("/api/chats").json()  # made by visitor A
    url = f"/api/chats/{chat['id']}"
    file = client.post(f"{url}/files", files={"file": ("a.md", b"# A", "text/markdown")}).json()
    upload = {"file": ("b.md", b"# B", "text/markdown")}

    assert client.get("/api/chats", headers=OTHER).json() == []  # list
    assert client.get(url, headers=OTHER).status_code == 404  # open
    assert client.patch(url, json={"title": "x"}, headers=OTHER).status_code == 404  # rename
    assert client.get(f"{url}/files", headers=OTHER).status_code == 404  # file chips
    assert client.post(f"{url}/files", files=upload, headers=OTHER).status_code == 404
    assert client.delete(f"{url}/files/{file['id']}", headers=OTHER).status_code == 404
    ask = client.post(f"{url}/messages", json={"question": "q"}, headers=OTHER)
    assert ask.status_code == 404
    assert client.delete(url, headers=OTHER).status_code == 404  # delete

    # Visitor A still has everything, untouched.
    assert client.get(url).json()["title"] == "New chat"
    assert [f["id"] for f in client.get(f"{url}/files").json()] == [file["id"]]
    assert api.app.state.qdrant.deleted == []  # B deleted no vectors


def test_each_visitor_lists_only_their_own_chats(client) -> None:
    mine = client.post("/api/chats").json()
    theirs = client.post("/api/chats", headers=OTHER).json()
    assert [c["id"] for c in client.get("/api/chats").json()] == [mine["id"]]
    assert [c["id"] for c in client.get("/api/chats", headers=OTHER).json()] == [theirs["id"]]


def test_public_mode_refuses_with_429_and_a_clear_message(client, monkeypatch) -> None:
    def fake_turn(*args):
        yield {"type": "done", "answer": "", "status": "ok", "sources": [], "timings": {}}

    monkeypatch.setattr(chat_api, "run_turn", fake_turn)
    monkeypatch.setattr(config, "PUBLIC_MODE", True)
    monkeypatch.setattr(config, "QUESTION_LIMITS", {"visitor": [(1, 60)]})
    chat_api.limits.reset()
    url = f"/api/chats/{client.post('/api/chats').json()['id']}/messages"
    assert client.post(url, json={"question": "q"}).status_code == 200
    refused = client.post(url, json={"question": "q"})
    assert refused.status_code == 429
    assert refused.json()["detail"] == chat_api.limits.MESSAGES[60]
    chat_api.limits.reset()


def test_files_per_chat_limit(client, monkeypatch) -> None:
    monkeypatch.setattr(config, "MAX_FILES_PER_CHAT", 1)
    url = f"/api/chats/{client.post('/api/chats').json()['id']}/files"
    assert client.post(url, files={"file": ("a.md", b"# A", "text/markdown")}).status_code == 202
    second = client.post(url, files={"file": ("b.md", b"# B", "text/markdown")})
    assert second.status_code == 400
    assert "already has 1 files" in second.json()["detail"]


# --- A3 + A4: answer seats and the "busy" message ---


def groq_429() -> RateLimitError:
    """What the openai library raises when Groq still says 429 after its retries."""
    response = httpx.Response(429, request=httpx.Request("POST", "https://api.groq.com"))
    return RateLimitError("rate limit", response=response, body=None)


def events_of(response) -> list[dict]:
    return [json.loads(line[6:]) for line in response.text.splitlines() if line]


@pytest.fixture
def one_seat(monkeypatch):
    seats = threading.BoundedSemaphore(1)
    monkeypatch.setattr(chat_api.limits, "_answer_seats", seats)
    monkeypatch.setattr(config, "QUEUE_WAIT_SECONDS", 0.05)
    return seats


def test_full_queue_says_waiting_then_busy(client, one_seat) -> None:
    one_seat.acquire()  # someone else is being answered
    url = f"/api/chats/{client.post('/api/chats').json()['id']}/messages"
    events = events_of(client.post(url, json={"question": "q"}))
    assert [event["type"] for event in events] == ["stage", "error"]
    assert events[1]["message"] == chat_api.limits.BUSY


def test_groq_429_becomes_the_busy_message_and_frees_the_seat(
    client, one_seat, monkeypatch
) -> None:
    def rate_limited_turn(*args):
        raise groq_429()
        yield  # makes this a generator

    monkeypatch.setattr(chat_api, "run_turn", rate_limited_turn)
    url = f"/api/chats/{client.post('/api/chats').json()['id']}/messages"
    events = events_of(client.post(url, json={"question": "q"}))
    assert events == [{"type": "error", "message": chat_api.limits.BUSY}]
    assert one_seat.acquire(blocking=False)  # the seat came back


def test_ask_endpoint_busy_is_503(client, one_seat, monkeypatch) -> None:
    def rate_limited_ask(*args):
        raise groq_429()

    monkeypatch.setattr(api, "ask", rate_limited_ask)
    response = client.post("/ask", json={"question": "q"})
    assert (response.status_code, response.json()["detail"]) == (503, chat_api.limits.BUSY)
    assert one_seat.acquire(blocking=False)  # freed after the error too
    response = client.post("/ask", json={"question": "q"})  # now the only seat is taken
    assert response.status_code == 503


# --- A7: readiness ---


def test_ready_when_models_qdrant_library_and_llm_are_there(client, monkeypatch) -> None:
    monkeypatch.setattr(api.app.state, "models_ready", True, raising=False)
    monkeypatch.setattr(config, "LLM_MODEL", "some-model")
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"models": True, "qdrant": True, "library": True, "llm_configured": True},
    }


def test_not_ready_when_qdrant_is_down(client, monkeypatch) -> None:
    def down(name):
        raise ConnectionError("qdrant unreachable")

    monkeypatch.setattr(api.app.state, "models_ready", True, raising=False)
    monkeypatch.setattr(config, "LLM_MODEL", "some-model")
    monkeypatch.setattr(api.app.state.qdrant, "collection_exists", down)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["qdrant"] is False
    assert client.get("/health").status_code == 200  # alive, just not ready


@pytest.mark.parametrize("bad", ["", "short", "x" * 65, "a' OR '1'='1' --------"])
def test_missing_or_bad_visitor_id_is_refused(client, bad) -> None:
    response = client.get("/api/chats", headers={"X-Visitor-Id": bad})
    assert response.status_code == 400
    assert client.get("/api/health", headers={"X-Visitor-Id": bad}).status_code == 200

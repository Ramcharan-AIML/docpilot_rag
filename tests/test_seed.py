"""Tests for the seed step's decisions (B4). Qdrant is a fake; the real restore is checked
by hand on the laptop's prod stack (it needs Qdrant as a server)."""

from types import SimpleNamespace

from docpilot import config
from docpilot.store import seed


class FakeQdrant:
    def __init__(self, chunks: int):
        self.chunks = chunks

    def collection_exists(self, name):
        return self.chunks > 0

    def count(self, name, exact=True):
        return SimpleNamespace(count=self.chunks)


def test_existing_library_is_left_alone(tmp_path, monkeypatch) -> None:
    uploads = []
    monkeypatch.setattr(seed, "upload_snapshot", lambda *args: uploads.append(args))
    assert seed.seed(FakeQdrant(413), tmp_path / "x.snapshot").startswith("skipped")
    assert uploads == []


def test_empty_qdrant_is_seeded_with_the_checksum(tmp_path, monkeypatch) -> None:
    qdrant = FakeQdrant(0)
    snapshot = tmp_path / "docpilot_public.snapshot"
    snapshot.write_bytes(b"data")
    snapshot.with_suffix(".sha256").write_text("abc123\n", encoding="utf-8")

    def fake_upload(client, path, collection, checksum):
        assert (path, collection, checksum) == (snapshot, config.COLLECTION_NAME, "abc123")
        client.chunks = 413

    monkeypatch.setattr(seed, "upload_snapshot", fake_upload)
    assert seed.seed(qdrant, snapshot) == f"restored {config.COLLECTION_NAME}: 413 chunks"


def test_force_replaces_an_existing_library(tmp_path, monkeypatch) -> None:
    uploads = []
    monkeypatch.setattr(seed, "upload_snapshot", lambda *args: uploads.append(args))
    seed.seed(FakeQdrant(413), tmp_path / "x.snapshot", force=True)
    assert len(uploads) == 1

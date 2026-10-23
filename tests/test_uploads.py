"""Tests for uploads (D-061). Real tiny PDFs (made with pypdfium2), real local-mode Qdrant in
a temp folder; the embedding models are replaced by fakes (fast, offline)."""

import pypdfium2
import pytest

from docpilot import config
from docpilot.ingestion import uploads
from docpilot.ingestion.uploads import (
    UploadError,
    check_bytes,
    read_text,
    safe_filename,
    save_upload,
)
from docpilot.store.qdrant_store import chat_filter, chunks_per_source, get_client, search


def make_pdf(path, pages: int) -> bytes:
    """A real PDF with `pages` empty pages."""
    document = pypdfium2.PdfDocument.new()
    for _ in range(pages):
        document.new_page(200, 200)
    document.save(str(path))
    document.close()
    return path.read_bytes()


@pytest.mark.parametrize(
    ("name", "safe"),
    [
        ("notes.pdf", "notes.pdf"),
        ("My Notes (v2).PDF", "My_Notes_v2_.PDF"),
        ("../../secret/a b.pdf", "a_b.pdf"),  # no folder tricks: we choose where files go
        ("C:\\Users\\x\\readme.md", "readme.md"),
        ("todo.txt", "todo.txt"),
    ],
)
def test_safe_filename(name: str, safe: str) -> None:
    assert safe_filename(name) == safe


def test_other_file_types_are_refused() -> None:
    with pytest.raises(UploadError, match="Only PDF, Markdown"):
        safe_filename("setup.exe")


def test_bytes_are_checked() -> None:
    with pytest.raises(UploadError, match="not a real PDF"):
        check_bytes("a.pdf", b"MZ\x90\x00 an exe renamed to .pdf")
    with pytest.raises(UploadError, match="empty"):
        check_bytes("a.md", b"")
    with pytest.raises(UploadError, match="not UTF-8"):
        check_bytes("a.txt", b"\xff\xfe\x00binary")
    check_bytes("a.md", "# Ünïcode is fine".encode())


def test_too_big_file_is_refused(monkeypatch) -> None:
    monkeypatch.setattr(config, "MAX_UPLOAD_MB", 0)
    with pytest.raises(UploadError, match="over 0 MB"):
        check_bytes("a.pdf", b"%PDF-1.7 tiny")


def test_save_puts_the_file_in_the_chat_folder(tmp_path) -> None:
    data = make_pdf(tmp_path / "source.pdf", pages=3)
    path, name, source, pages = save_upload("week 1.pdf", data, "chat1", folder=tmp_path)
    assert path == tmp_path / "chat1" / "week_1.pdf"
    assert (name, source, pages) == ("week_1.pdf", "uploads/chat1/week_1.pdf", 3)


def test_too_many_pages_is_refused_and_not_kept(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(config, "MAX_UPLOAD_PAGES", 2)
    data = make_pdf(tmp_path / "source.pdf", pages=3)
    with pytest.raises(UploadError, match="3 pages: the limit is 2"):
        save_upload("big.pdf", data, "chat1", folder=tmp_path)
    assert not (tmp_path / "chat1" / "big.pdf").exists()


def test_broken_pdf_is_refused(tmp_path) -> None:
    with pytest.raises(UploadError, match="could not be opened"):
        save_upload("broken.pdf", b"%PDF-1.7 but nothing after", "chat1", folder=tmp_path)


def test_pdf_pages_get_page_headings(tmp_path, monkeypatch) -> None:
    path = tmp_path / "a.pdf"
    path.write_bytes(b"%PDF")
    monkeypatch.setattr(uploads, "pdf_pages", lambda p: ["first\r\npage", "second"])
    assert read_text(path) == "# Page 1\n\nfirst\npage\n\n# Page 2\n\nsecond"


@pytest.fixture
def fake_models(monkeypatch):
    """Fixed vectors instead of BGE / BM25: the tests are about storing and filtering."""
    monkeypatch.setattr(
        uploads, "embed_documents", lambda texts: [[1.0] + [0.0] * 383 for _ in texts]
    )
    monkeypatch.setattr(
        uploads,
        "embed_sparse_documents",
        lambda texts, avg: [{"indices": [1], "values": [1.0]} for _ in texts],
    )


def write(tmp_path, name: str, text: str):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_chats_only_see_their_own_files(tmp_path, fake_models) -> None:
    client = get_client(tmp_path / "qdrant")
    try:
        a = write(tmp_path, "a.md", "# A\n\nFile of chat one.")
        b = write(tmp_path, "b.md", "# B\n\nFile of chat two.")
        uploads.ingest_file(a, "uploads/one/a.md", "one", client, "test_uploads")
        uploads.ingest_file(b, "uploads/two/b.md", "two", client, "test_uploads")

        vector = [1.0] + [0.0] * 383
        hits = search(client, "test_uploads", vector, 10, query_filter=chat_filter("one"))
        assert [hit["source"] for hit in hits] == ["uploads/one/a.md"]
        assert hits[0]["chat_id"] == "one"
    finally:
        client.close()


def test_reupload_replaces_old_chunks(tmp_path, fake_models) -> None:
    client = get_client(tmp_path / "qdrant")
    try:
        long = write(tmp_path, "a.md", "# Notes\n\n" + "Path parameters are typed. " * 300)
        first = uploads.ingest_file(long, "uploads/one/a.md", "one", client, "test_uploads")
        assert first["chunks"] > 1

        short = write(tmp_path, "a.md", "# Notes\n\nNow one short page.")
        uploads.ingest_file(short, "uploads/one/a.md", "one", client, "test_uploads")
        assert chunks_per_source(client, "test_uploads") == {"uploads/one/a.md": 1}
    finally:
        client.close()


def test_file_without_text_is_refused(tmp_path, fake_models, monkeypatch) -> None:
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"%PDF")
    monkeypatch.setattr(uploads, "pdf_pages", lambda p: ["", "  "])  # pages of pictures
    client = get_client(tmp_path / "qdrant")
    try:
        with pytest.raises(UploadError, match="No text found"):
            uploads.ingest_file(path, "uploads/one/scan.pdf", "one", client, "test_uploads")
    finally:
        client.close()

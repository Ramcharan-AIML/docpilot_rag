"""Tests for loader.py. Each test builds a tiny fake docs folder in pytest's tmp_path."""

from pathlib import Path

import pytest

from docpilot.ingestion.loader import load_documents


def test_loads_md_and_txt_with_relative_sources(tmp_path: Path) -> None:
    (tmp_path / "fastapi").mkdir()
    (tmp_path / "fastapi" / "query.md").write_text("# Query params", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("plain text", encoding="utf-8")

    docs = load_documents(tmp_path)

    sources = [doc.source for doc in docs]
    assert sources == ["fastapi/query.md", "notes.txt"]  # sorted, forward slashes
    assert docs[0].text == "# Query params"


def test_ignores_unsupported_files(tmp_path: Path) -> None:
    (tmp_path / "keep.md").write_text("keep me", encoding="utf-8")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG")
    (tmp_path / ".gitkeep").write_text("", encoding="utf-8")

    docs = load_documents(tmp_path)

    assert [doc.source for doc in docs] == ["keep.md"]


def test_folder_named_like_a_file_is_skipped(tmp_path: Path) -> None:
    # A folder called "old.md" must not crash read_text().
    (tmp_path / "old.md").mkdir()

    assert load_documents(tmp_path) == []


def test_missing_folder_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_documents(tmp_path / "does_not_exist")

"""Tests for ingestion/metadata.py."""

import hashlib

import pytest

from docpilot.ingestion.chunkers.base import Chunk
from docpilot.ingestion.metadata import add_metadata, heading_path_at, scan_lines

DOC = (
    "# Query Parameters { #query-parameters }\n"  # offset 0
    "Intro text.\n"
    "## Defaults { #defaults }\n"
    "Default values.\n"
    "```python\n"
    "# a comment, not a heading\n"
    "skip: int = 0\n"
    "```\n"
    "| name | default |\n"
    "|---|---|\n"
    "## Optional\n"
    "Use None.\n"
)


def chunk_at(text_piece: str, source: str = "fastapi/query-params.md") -> Chunk:
    return Chunk(text=text_piece, source=source, chunk_number=0, char_start=DOC.index(text_piece))


def test_heading_path_nests_and_drops_anchors():
    lines = scan_lines(DOC)
    assert heading_path_at(lines, DOC.index("Intro")) == ["Query Parameters"]
    assert heading_path_at(lines, DOC.index("Default values")) == ["Query Parameters", "Defaults"]
    assert heading_path_at(lines, DOC.index("Use None")) == ["Query Parameters", "Optional"]


def test_hash_comment_in_code_is_not_a_heading():
    lines = scan_lines(DOC)
    assert heading_path_at(lines, DOC.index("skip: int")) == ["Query Parameters", "Defaults"]


def test_flags_and_source_facts():
    (code_chunk,) = add_metadata([chunk_at("```python\n# a comment")], DOC)
    assert code_chunk.has_code and not code_chunk.has_table
    (table_chunk,) = add_metadata([chunk_at("| name | default |")], DOC)
    assert table_chunk.has_table and not table_chunk.has_code
    assert table_chunk.technology == "fastapi" and table_chunk.domain == "docs"
    assert table_chunk.doc_type == "tutorial" and len(table_chunk.version) == 40


def test_content_hash_is_sha256_of_text():
    (chunk,) = add_metadata([chunk_at("Intro text.")], DOC)
    assert chunk.content_hash == hashlib.sha256(b"Intro text.").hexdigest()


def test_unknown_source_fails_loudly():
    with pytest.raises(KeyError):
        add_metadata([chunk_at("Intro text.", source="mystery/page.md")], DOC)

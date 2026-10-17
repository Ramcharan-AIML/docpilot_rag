"""Give every chunk metadata: where it came from and what is inside it (step 2.5).

Why: Phase 3 filters by technology/domain/version, citations can show the section
("Query Parameters > Defaults"), and content_hash spots duplicates. Metadata goes into the
Qdrant payload only; the embedded text is unchanged (so C0 numbers do not move).
"""

import hashlib
from dataclasses import dataclass

from docpilot.ingestion.blocks import FENCE, parse_heading
from docpilot.ingestion.chunkers.base import Chunk
from docpilot.ingestion.sources import SOURCES


@dataclass
class Line:
    start: int  # character offset of the line in the document
    text: str
    in_code: bool  # inside a ``` block (fence lines included)


def scan_lines(text: str) -> list[Line]:
    """Every line with its offset and whether it belongs to a code block."""
    lines, offset, inside = [], 0, False
    for raw in text.splitlines(keepends=True):
        is_fence = raw.strip().startswith(FENCE)
        lines.append(Line(offset, raw.rstrip("\r\n"), inside or is_fence))
        if is_fence:
            inside = not inside
        offset += len(raw)
    return lines


def heading_path_at(lines: list[Line], offset: int) -> list[str]:
    """The headings above `offset`, outermost first: ["Query Parameters", "Defaults"].

    Lines inside code blocks are skipped: "# a comment" in Python is not a heading.
    Used for fixed-size chunks, which do not follow blocks; block-based chunkers (2.6)
    take heading_path straight from their Blocks.
    """
    path: list[str] = []
    for line in lines:
        if line.start > offset:
            break
        heading = None if line.in_code else parse_heading(line.text)
        if heading is not None:
            level, title = heading  # same rule as blocks.py (one definition)
            path = path[: level - 1] + [title]
    return path


def content_flags(lines: list[Line], start: int, end: int) -> tuple[bool, bool]:
    """(has_code, has_table) for the text between start and end."""
    inside = [line for line in lines if start <= line.start + len(line.text) and line.start < end]
    has_code = any(line.in_code for line in inside)
    # A Markdown table row: starts with "|" and has at least two of them, outside code.
    has_table = any(
        not line.in_code and line.text.lstrip().startswith("|") and line.text.count("|") >= 2
        for line in inside
    )
    return has_code, has_table


def technology_of(source: str) -> str:
    """'fastapi/query-params.md' -> 'fastapi' (the first folder under data/docs/)."""
    return source.split("/", 1)[0]


def add_metadata(chunks: list[Chunk], document_text: str) -> list[Chunk]:
    """Fill the metadata fields of one document's chunks (in place) and return them.

    `document_text` must be the text the chunker saw (after cleaning and includes), so
    each chunk's char_start points to the right place.
    """
    lines = scan_lines(document_text)
    for chunk in chunks:
        technology = technology_of(chunk.source)
        if technology not in SOURCES:
            # Fail loudly: a document without a register entry has no known licence (D-030).
            raise KeyError(f"{chunk.source}: no entry for {technology!r} in ingestion/sources.py")
        info = SOURCES[technology]
        chunk.technology = technology
        chunk.domain, chunk.doc_type, chunk.version = info.domain, info.doc_type, info.version
        chunk.heading_path = heading_path_at(lines, chunk.char_start)
        end = chunk.char_start + len(chunk.text)
        chunk.has_code, chunk.has_table = content_flags(lines, chunk.char_start, end)
        chunk.content_hash = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
    return chunks

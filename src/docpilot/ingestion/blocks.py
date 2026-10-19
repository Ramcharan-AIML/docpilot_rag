"""Split Markdown into blocks: heading, paragraph, code, table, list (step 2.4).

Why: fixed-size chunks cut through code, tables and lists (failure log Q5, Q6; q-018).
Blocks are the units later chunkers (2.6) keep whole. Hand-written instead of
markdown-it-py (Rule 8: see it raw first); our docs use a small subset of Markdown.
Known limits: a list item that continues on an unmarked next line becomes a paragraph;
HTML tables and nested block quotes are not recognised.
"""

import re
from dataclasses import dataclass, field

FENCE = "```"
# FastAPI headings end with an anchor: "## Defaults { #defaults }" -> "Defaults"
HEADING_ANCHOR = re.compile(r"\s*\{\s*#[^}]*\}\s*$")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")  # "#hashtag" (no space) is not a heading
LIST_ITEM = re.compile(r"^\s*(?:[*+-]|\d+[.)])\s")  # "* a", "- a", "1. a" (also indented)


@dataclass
class Block:
    kind: str  # heading | paragraph | code | table | list
    text: str
    heading_path: list[str] = field(default_factory=list)
    # Character positions in the document: text == document[start:end]. Chunkers (2.6)
    # cut the document at these positions, so chunk text is always an exact slice.
    start: int = 0
    end: int = 0


def parse_heading(line: str) -> tuple[int, str] | None:
    """'## Defaults { #defaults }' -> (2, 'Defaults'); not a heading -> None.

    Shared with metadata.py, so both always read headings the same way.
    """
    match = HEADING.match(line)
    if match is None:
        return None
    return len(match.group(1)), HEADING_ANCHOR.sub("", match.group(2)).strip()


def line_kind(line: str) -> str:
    """Kind of one non-code, non-heading line."""
    stripped = line.lstrip()
    if stripped.startswith("|"):
        return "table"
    if LIST_ITEM.match(line):
        return "list"
    return "paragraph"


def parse_blocks(text: str) -> list[Block]:
    blocks: list[Block] = []
    heading_path: list[str] = []
    buffer: list[str] = []
    buffer_kind = "paragraph"
    buffer_start = 0  # character position where the buffer's first line starts
    inside_code = False

    def flush() -> None:
        if buffer and "".join(buffer).strip():
            joined = "\n".join(buffer)
            end = buffer_start + len(joined)
            blocks.append(Block(buffer_kind, joined, list(heading_path), buffer_start, end))
        buffer.clear()

    offset = 0  # character position of the current line
    for raw in text.splitlines(keepends=True):
        line_start, offset = offset, offset + len(raw)
        line = raw.rstrip("\r\n")
        if not buffer:
            buffer_start = line_start  # a new block would start on this line
        if line.strip().startswith(FENCE):
            if not inside_code:
                flush()  # whatever came before the code is finished
                buffer_kind = "code"
                buffer_start = line_start
            buffer.append(line)
            if inside_code:
                flush()  # the closing fence ends the code block
                buffer_kind = "paragraph"
            inside_code = not inside_code
            continue
        if inside_code:
            buffer.append(line)  # blank lines and "# comments" stay inside the code
            continue
        heading = parse_heading(line)
        if heading is not None:
            flush()
            level, title = heading
            heading_path[:] = heading_path[: level - 1] + [title]
            end = line_start + len(line)
            blocks.append(Block("heading", title, list(heading_path), line_start, end))
            continue
        kind = line_kind(line) if line.strip() else buffer_kind
        if line.strip() == "" or kind != buffer_kind:
            flush()  # a blank line or a change of kind ends the current block
            buffer_kind = kind
        if line.strip():
            if not buffer:
                buffer_start = line_start
            buffer.append(line)
    flush()  # also keeps an unclosed code block at the end of the file
    return blocks

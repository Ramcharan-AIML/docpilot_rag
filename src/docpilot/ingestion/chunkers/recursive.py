"""Recursive chunking (C1): cut at the biggest natural break that makes the pieces fit.

Like tearing a book at chapter breaks, and only tearing inside a chapter when it is too
thick. Text-based on purpose, the same idea as LangChain's RecursiveCharacterTextSplitter:
it knows separators, not Markdown, so a blank line inside a code block is a break too.
The structure-aware chunker is hierarchical.py (C4); comparing the two is the point.

Works on (start, end) character spans of the document, so every chunk is an exact slice
and keeps its position (char_start) for metadata and citations.
"""

from docpilot.ingestion.chunkers.base import Chunk
from docpilot.ingestion.chunkers.fixed import check_sizes
from docpilot.ingestion.chunkers.tokens import MAX_CHUNK_TOKENS, count_tokens, token_offsets

# Biggest break first: section, subsection, paragraph, line, sentence, word (plan 2.6).
SEPARATORS = ["\n## ", "\n### ", "\n\n", "\n", ". ", " "]

Span = tuple[int, int]  # (start, end) character positions in the document


def span_tokens(text: str, span: Span) -> int:
    return count_tokens(text[span[0] : span[1]])


def split_span(text: str, span: Span, separator: str) -> list[Span]:
    """Cut `span` one character after the start of every `separator`.

    "\\n## Title": the newline ends the previous piece, "## Title" starts the next one
    (a heading stays with its section). ". ": the full stop stays with its sentence.
    """
    start, end = span
    pieces, piece_start = [], start
    position = text.find(separator, start, end)
    while position != -1:
        cut = position + 1
        if cut < end:
            pieces.append((piece_start, cut))
            piece_start = cut
        position = text.find(separator, cut, end)
    pieces.append((piece_start, end))
    return pieces


def hard_cut(text: str, span: Span, max_tokens: int) -> list[Span]:
    """Last resort (no separator left): cut every `max_tokens` tokens."""
    start = span[0]
    offsets = token_offsets(text[span[0] : span[1]])
    return [
        (start + offsets[first][0], start + offsets[min(first + max_tokens, len(offsets)) - 1][1])
        for first in range(0, len(offsets), max_tokens)
    ]


def recursive_split(text: str, span: Span, max_tokens: int, separators: list[str]) -> list[Span]:
    """Pieces of `span` that each fit in `max_tokens`, using the biggest separator that works."""
    if span_tokens(text, span) <= max_tokens:
        return [span]
    for index, separator in enumerate(separators):
        pieces = split_span(text, span, separator)
        if len(pieces) > 1:  # this separator is in the text: use it, smaller ones below
            results: list[Span] = []
            for piece in pieces:
                results.extend(recursive_split(text, piece, max_tokens, separators[index + 1 :]))
            return results
    return hard_cut(text, span, max_tokens)


def merge_small_pieces(text: str, pieces: list[Span], max_tokens: int, overlap: int) -> list[Span]:
    """Glue neighbouring pieces together up to `max_tokens`; repeat up to `overlap` tokens.

    Pieces are neighbours in the document, so a merged span is one continuous slice.
    """
    merged: list[Span] = []
    current: list[Span] = []
    for piece in pieces:
        if current and span_tokens(text, (current[0][0], piece[1])) > max_tokens:
            merged.append((current[0][0], current[-1][1]))
            # Overlap: the last pieces of this chunk (up to `overlap` tokens) start the next.
            carry: list[Span] = []
            for previous in reversed(current):
                if span_tokens(text, (previous[0], current[-1][1])) > overlap:
                    break
                carry.insert(0, previous)
            current = carry
            while current and span_tokens(text, (current[0][0], piece[1])) > max_tokens:
                current.pop(0)  # the overlap must never push a chunk over the size
        current.append(piece)
    if current:
        merged.append((current[0][0], current[-1][1]))
    return merged


def trim(text: str, span: Span) -> Span:
    """Move the borders inwards past spaces and line breaks."""
    start, end = span
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def recursive_chunks(text: str, source: str, chunk_tokens: int, overlap_tokens: int) -> list[Chunk]:
    """Split one document recursively, then merge small neighbours up to `chunk_tokens`."""
    check_sizes(chunk_tokens, overlap_tokens)
    if chunk_tokens > MAX_CHUNK_TOKENS:
        raise ValueError(f"chunk_tokens must be at most {MAX_CHUNK_TOKENS}")
    pieces = recursive_split(text, (0, len(text)), chunk_tokens, SEPARATORS)
    chunks: list[Chunk] = []
    for span in merge_small_pieces(text, pieces, chunk_tokens, overlap_tokens):
        start, end = trim(text, span)
        if start < end:
            chunks.append(
                Chunk(
                    text=text[start:end],
                    source=source,
                    chunk_number=len(chunks),
                    strategy="recursive",
                    char_start=start,
                )
            )
    return chunks

"""Q&A-pair chunking (D-030, interview-prep files): never separate a question from its answer.

A pair starts at a question line, "### Q3. ..." (our docs/interview files) or "**Q:** ...",
and ends where the next question or a higher heading starts. One pair = one chunk. A long
answer is split, and every piece gets the question as its prefix, so each piece is still
found by the question. Text that is not inside a pair (intros) is chunked recursively.
Used from step 2.8, when interview files join the corpus.
"""

import re

from docpilot.ingestion.blocks import parse_heading
from docpilot.ingestion.chunkers.base import Chunk
from docpilot.ingestion.chunkers.recursive import (
    SEPARATORS,
    Span,
    merge_small_pieces,
    recursive_split,
    trim,
)
from docpilot.ingestion.chunkers.tokens import MAX_CHUNK_TOKENS, count_tokens

QUESTION = re.compile(r"^(?:#{2,6}\s+Q\d+[.:)]|\*\*Q\d*[.:]?\*\*|\*\*Q\d*[.:])")


def find_pairs(text: str) -> list[tuple[Span, str]]:
    """(span, question line) for every pair, in order; question is "" for text outside pairs."""
    parts: list[tuple[Span, str]] = []
    part_start, question, question_level = 0, "", 7
    offset = 0
    for raw in text.splitlines(keepends=True):
        line_start, offset = offset, offset + len(raw)
        line = raw.rstrip("\r\n")
        heading = parse_heading(line)
        starts_pair = QUESTION.match(line) is not None
        ends_pair = heading is not None and heading[0] < question_level
        if starts_pair or (question and ends_pair):
            parts.append(((part_start, line_start), question))
            part_start = line_start
            question = line if starts_pair else ""
            question_level = heading[0] if (starts_pair and heading) else 7
    parts.append(((part_start, len(text)), question))
    return [(trim(text, span), q) for span, q in parts if text[span[0] : span[1]].strip()]


def qa_pair_chunks(
    text: str, source: str, chunk_tokens: int, overlap_tokens: int = 0
) -> list[Chunk]:
    if not 0 < chunk_tokens <= MAX_CHUNK_TOKENS:
        raise ValueError(f"chunk_tokens must be between 1 and {MAX_CHUNK_TOKENS}")
    chunks: list[Chunk] = []
    for span, question in find_pairs(text):
        prefix = question + "\n\n" if question else ""
        room = chunk_tokens - count_tokens(prefix)
        if count_tokens(text[span[0] : span[1]]) <= chunk_tokens:
            pieces = [span]  # the normal case: the whole pair is one chunk
        else:
            pieces = merge_small_pieces(
                text, recursive_split(text, span, room, SEPARATORS), room, 0
            )
        for index, piece in enumerate(pieces):
            start, end = trim(text, piece)
            if start < end:
                # the first piece already starts with the question: no prefix needed there
                needs_prefix = bool(question) and (
                    index > 0 or not text[start:end].startswith(question)
                )
                chunks.append(
                    Chunk(
                        text=text[start:end],
                        source=source,
                        chunk_number=len(chunks),
                        strategy="qa_pairs",
                        char_start=start,
                        prefix=prefix if needs_prefix else "",
                    )
                )
    return chunks

"""Semantic chunking (C2): cut where the topic changes.

1. Units: sentences of paragraphs; code, tables, lists and headings stay one unit each
   (a code block has no "sentences").
2. Embed every unit; similarity of each unit with the next one (vectors are normalised,
   so the dot product is the cosine).
3. A new chunk starts where that similarity is in the lowest `percentile` percent of this
   document (a "topic jump"), or where the next unit would pass the size cap.
Cost: one embedding per sentence at ingest time (CPU), on top of one per chunk.
"""

import math
import re
from itertools import pairwise

from docpilot import config
from docpilot.embedding.dense import embed_documents
from docpilot.ingestion.blocks import parse_blocks
from docpilot.ingestion.chunkers.base import Chunk
from docpilot.ingestion.chunkers.recursive import SEPARATORS, Span, recursive_split, trim
from docpilot.ingestion.chunkers.tokens import MAX_CHUNK_TOKENS, count_tokens

SENTENCE_END = re.compile(r"[.!?](?=\s)")  # ". " ends a sentence; "model_name.value" does not


def sentence_spans(text: str, span: Span) -> list[Span]:
    """Sentences of one paragraph, as spans (the full stop stays with its sentence)."""
    start, end = span
    pieces, piece_start = [], start
    for match in SENTENCE_END.finditer(text, start, end):
        pieces.append((piece_start, match.end()))
        piece_start = match.end()
    pieces.append((piece_start, end))
    return [trim(text, piece) for piece in pieces if text[piece[0] : piece[1]].strip()]


def semantic_units(text: str) -> list[Span]:
    units: list[Span] = []
    for block in parse_blocks(text):
        if block.kind == "paragraph":
            units.extend(sentence_spans(text, (block.start, block.end)))
        else:
            units.append((block.start, block.end))
    return units


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile (same rule as evals/metrics.py; src cannot import evals)."""
    ordered = sorted(values)
    rank = math.ceil(p / 100 * len(ordered))  # 1-based rank
    return ordered[max(rank, 1) - 1]


def semantic_chunks(
    text: str,
    source: str,
    chunk_tokens: int,
    overlap_tokens: int = 0,
    percentile_cut: float = config.SEMANTIC_PERCENTILE,
) -> list[Chunk]:
    """Topic-based chunks of at most `chunk_tokens` (unless one unit alone is bigger)."""
    if not 0 < chunk_tokens <= MAX_CHUNK_TOKENS:
        raise ValueError(f"chunk_tokens must be between 1 and {MAX_CHUNK_TOKENS}")
    units = semantic_units(text)
    if not units:
        return []
    vectors = embed_documents([text[start:end] for start, end in units])
    similarity = [
        sum(a * b for a, b in zip(left, right, strict=True))
        for left, right in pairwise(vectors)  # (unit 0, unit 1), (unit 1, unit 2) ...
    ]
    threshold = percentile(similarity, percentile_cut) if similarity else 0.0

    groups: list[Span] = []
    group_start, group_end = units[0]
    for index, (start, end) in enumerate(units[1:]):
        topic_jump = similarity[index] <= threshold
        too_big = count_tokens(text[group_start:end]) > chunk_tokens
        if topic_jump or too_big:
            groups.append((group_start, group_end))
            group_start = start
        group_end = end
    groups.append((group_start, group_end))

    chunks: list[Chunk] = []
    for group in groups:
        # Only a unit bigger than the MODEL limit is split further.
        for start, end in (
            trim(text, piece)
            for piece in recursive_split(text, group, MAX_CHUNK_TOKENS, SEPARATORS)
        ):
            if start < end:
                chunks.append(
                    Chunk(
                        text=text[start:end],
                        source=source,
                        chunk_number=len(chunks),
                        strategy="semantic",
                        char_start=start,
                    )
                )
    return chunks

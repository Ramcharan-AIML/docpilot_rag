"""Hierarchical (structure-aware) chunking (C4): follow the document's own layout.

Like cutting a cake along its layers instead of with a ruler. Uses the blocks of step 2.4:
- a heading always starts a new chunk (a chunk never mixes two sections);
- blocks of one section are grouped until the size is reached;
- a code block, table or list is never split (unless it alone is over the model limit,
  which no block in our pages is: the largest is 228 tokens);
- the heading path ("Query Parameters > Defaults") is put in front for embedding, so a
  short chunk still "knows" its topic. The chunk text itself stays an exact slice.
"""

from docpilot.ingestion.blocks import Block, parse_blocks
from docpilot.ingestion.chunkers.base import Chunk, heading_prefix
from docpilot.ingestion.chunkers.recursive import SEPARATORS, recursive_split, trim
from docpilot.ingestion.chunkers.tokens import MAX_CHUNK_TOKENS, count_tokens


def group_blocks(text: str, blocks: list[Block], size: int) -> list[list[Block]]:
    """Blocks -> groups; each group becomes one chunk (or more, if one block is huge).

    The size counts the text only, not the heading prefix: then "with prefix" and "without
    prefix" make the SAME chunks, and their two eval rows differ in one thing only.
    """

    def chunk_tokens(group: list[Block]) -> int:
        return count_tokens(text[group[0].start : group[-1].end])

    groups: list[list[Block]] = []
    group: list[Block] = []
    for block in blocks:
        only_headings = all(member.kind == "heading" for member in group)
        if block.kind == "heading" and not only_headings:
            groups.append(group)  # new section: close the old one
            group = [block]
        elif group and not only_headings and chunk_tokens([*group, block]) > size:
            groups.append(group)  # full: the next block starts a new chunk, same section
            group = [block]
        else:
            group.append(block)  # headings right after each other stay together
    if group:
        groups.append(group)
    return groups


def hierarchical_chunks(
    text: str, source: str, chunk_tokens: int, overlap_tokens: int = 0, with_prefix: bool = True
) -> list[Chunk]:
    """Structure-aware chunks. `overlap_tokens` is ignored: blocks are natural borders."""
    if not 0 < chunk_tokens <= MAX_CHUNK_TOKENS:
        raise ValueError(f"chunk_tokens must be between 1 and {MAX_CHUNK_TOKENS}")
    strategy = "hierarchical" if with_prefix else "hierarchical_noprefix"
    chunks: list[Chunk] = []
    for group in group_blocks(text, parse_blocks(text), chunk_tokens):
        prefix = heading_prefix(group[-1].heading_path) if with_prefix else ""
        span = (group[0].start, group[-1].end)
        # Only a single block bigger than the MODEL limit is split (never just "big").
        room = MAX_CHUNK_TOKENS - count_tokens(prefix)
        for start, end in (
            trim(text, piece) for piece in recursive_split(text, span, room, SEPARATORS)
        ):
            if start < end:
                chunks.append(
                    Chunk(
                        text=text[start:end],
                        source=source,
                        chunk_number=len(chunks),
                        strategy=strategy,
                        char_start=start,
                        prefix=prefix,
                    )
                )
    return chunks

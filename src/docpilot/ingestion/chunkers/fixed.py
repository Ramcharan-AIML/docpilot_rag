"""Fixed-size chunking: cut every N characters (or tokens), neighbours share some text.

Deliberately naive (D-006): it cuts through words, code blocks and tables. Phase 2 measures
how much that hurts and replaces it. The character version stays so C0 can be rebuilt
exactly; the token version is the fair "fixed" row next to the Phase 2 chunkers (D-038).
"""

from docpilot import config
from docpilot.ingestion.chunkers.base import Chunk
from docpilot.ingestion.chunkers.tokens import MAX_CHUNK_TOKENS, token_offsets


def check_sizes(size: int, overlap: int) -> None:
    """Same rules for characters and tokens."""
    if size <= 0:
        raise ValueError("chunk size must be positive")
    if overlap < 0 or overlap >= size:
        # overlap >= size means step <= 0: the loop would never move forward
        raise ValueError("overlap must be >= 0 and smaller than the chunk size")


def fixed_size_chunks(
    text: str,
    source: str,
    chunk_size: int = config.CHUNK_SIZE,
    overlap: int = config.CHUNK_OVERLAP,
) -> list[Chunk]:
    """Split text into pieces of `chunk_size` characters.

    Each piece starts `chunk_size - overlap` characters after the previous one, so the last
    `overlap` characters of one chunk are repeated at the start of the next. A sentence cut
    at a border then still appears in one piece, if it is shorter than the overlap.
    """
    check_sizes(chunk_size, overlap)

    step = chunk_size - overlap  # 800 - 100 = 700 new characters per chunk
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        piece = text[start : start + chunk_size]
        if piece.strip():  # skip pieces that are only whitespace
            # len(chunks), not a loop counter: numbers stay 0, 1, 2 with no gaps after a skip
            chunks.append(
                Chunk(
                    text=piece,
                    source=source,
                    chunk_number=len(chunks),
                    strategy="fixed",
                    char_start=start,  # lets metadata find the heading above it
                )
            )
        if start + chunk_size >= len(text):
            break  # this piece already reached the end; another would only repeat text
        start += step
    return chunks


def fixed_token_chunks(
    text: str,
    source: str,
    chunk_tokens: int = config.CHUNK_TOKENS,
    overlap_tokens: int = config.CHUNK_OVERLAP_TOKENS,
) -> list[Chunk]:
    """Same idea as fixed_size_chunks, but N model tokens per chunk instead of N characters.

    The chunk text is sliced from the original document between the first and last token,
    so code keeps its exact spacing. Still cuts through code and lists: only the unit changed.
    """
    check_sizes(chunk_tokens, overlap_tokens)
    if chunk_tokens > MAX_CHUNK_TOKENS:
        # Bigger chunks would be cut off silently by the model (D-038): refuse instead.
        raise ValueError(f"chunk_tokens must be at most {MAX_CHUNK_TOKENS}")

    offsets = token_offsets(text)  # [(start_char, end_char), ...] one pair per token
    step = chunk_tokens - overlap_tokens  # 400 - 50 = 350 new tokens per chunk
    chunks: list[Chunk] = []
    for first in range(0, len(offsets), step):
        last = min(first + chunk_tokens, len(offsets)) - 1  # index of the chunk's last token
        start, end = offsets[first][0], offsets[last][1]
        chunks.append(
            Chunk(
                text=text[start:end],
                source=source,
                chunk_number=len(chunks),
                strategy="fixed_tokens",
                char_start=start,
            )
        )
        if last == len(offsets) - 1:
            break  # reached the end; another chunk would only repeat the overlap
    return chunks

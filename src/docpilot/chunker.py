"""Fixed-size chunking: cut every N characters, neighbours share some text.

Deliberately naive (D-006): it cuts through words, code blocks and tables. Phase 2 measures
how much that hurts and replaces it.
"""

from dataclasses import dataclass

from docpilot import config


@dataclass
class Chunk:
    text: str
    source: str
    chunk_number: int  # 0, 1, 2 ... inside one source; used in citations and point ids


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
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        # overlap >= chunk_size means step <= 0: the loop would never move forward
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    step = chunk_size - overlap  # 800 - 100 = 700 new characters per chunk
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        piece = text[start : start + chunk_size]
        if piece.strip():  # skip pieces that are only whitespace
            # len(chunks), not a loop counter: numbers stay 0, 1, 2 with no gaps after a skip
            chunks.append(Chunk(text=piece, source=source, chunk_number=len(chunks)))
        if start + chunk_size >= len(text):
            break  # this piece already reached the end; another would only repeat text
        start += step
    return chunks


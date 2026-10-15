"""What every chunker produces. Shared by all strategies, so the store and evals never care
which chunker made a chunk. Step 2.5 adds metadata fields (heading path, domain, ...)."""

from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source: str
    chunk_number: int  # 0, 1, 2 ... inside one source; used in citations and point ids

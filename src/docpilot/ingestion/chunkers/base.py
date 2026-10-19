"""What every chunker produces. Shared by all strategies, so the store and evals never care
which chunker made a chunk. Metadata fields (step 2.5) are filled by ingestion/metadata.py
and stored as the Qdrant payload, so later phases can filter and cite by them."""

from dataclasses import dataclass, field


@dataclass
class Chunk:
    text: str
    source: str
    chunk_number: int  # 0, 1, 2 ... inside one source; used in citations and point ids
    # --- set by the chunker ---
    strategy: str = ""  # "fixed", "recursive", ... (which chunker made it)
    char_start: int = 0  # where the chunk starts in the (cleaned) document text
    # Added in front of `text` for EMBEDDING only (heading path, LLM-written context).
    # `text` stays an exact slice of the document: that is what the LLM and the eval see.
    prefix: str = ""
    parent_id: str = ""  # parent-child only: which parent section this child belongs to
    # --- step 2.5 metadata (ingestion/metadata.py); defaults = "not filled yet" ---
    domain: str = ""  # docs | learning | interview (D-030)
    technology: str = ""  # first folder under data/docs/: fastapi, docker, ...
    doc_type: str = ""  # tutorial | reference | guide | notes
    version: str = ""  # docs version / commit that was downloaded
    heading_path: list[str] = field(default_factory=list)  # e.g. ["Query Parameters", "Defaults"]
    has_code: bool = False
    has_table: bool = False
    content_hash: str = ""  # sha256 of text: spot duplicates, re-embed only what changed


def embedding_text(chunk: Chunk) -> str:
    """What the embedding model reads for this chunk: prefix (if any) + text."""
    return chunk.prefix + chunk.text


def heading_prefix(heading_path: list[str]) -> str:
    """["Query Parameters", "Defaults"] -> "Query Parameters > Defaults\n\n" ("" if none)."""
    return " > ".join(heading_path) + "\n\n" if heading_path else ""

"""Parent-child chunking (C3): search with small pieces, answer with the big piece.

Like a book index: you find the exact line (child), then read the whole page around it
(parent). Small children give sharp vectors; the parent gives the LLM enough context.
- parent = one section, built like a hierarchical chunk (blocks kept whole, no prefix),
  up to `parent_tokens`; parents are NOT embedded, so they may exceed the 510 limit;
- child = recursive pieces of one parent, `chunk_tokens` each; only children are indexed;
- parents are saved in data/processed/parents_<collection>.json (plan 2.6); search finds
  children, lift_to_parents() swaps each for its parent, without duplicates.
"""

import json
from pathlib import Path

from docpilot import config
from docpilot.ingestion.blocks import parse_blocks
from docpilot.ingestion.chunkers.base import Chunk
from docpilot.ingestion.chunkers.hierarchical import group_blocks
from docpilot.ingestion.chunkers.recursive import (
    SEPARATORS,
    merge_small_pieces,
    recursive_split,
    trim,
)


def parent_child_chunks(
    text: str,
    source: str,
    chunk_tokens: int = config.CHILD_TOKENS,
    overlap_tokens: int = 0,
    parent_tokens: int = config.PARENT_TOKENS,
    parents: dict[str, dict] | None = None,
) -> list[Chunk]:
    """Children of one document; their parents are added to `parents` (id -> parent)."""
    children: list[Chunk] = []
    groups = group_blocks(text, parse_blocks(text), parent_tokens)
    for number, group in enumerate(groups):
        parent_start, parent_end = trim(text, (group[0].start, group[-1].end))
        parent_id = f"{source}#p{number}"
        if parents is not None:
            parents[parent_id] = {
                "source": source,
                "text": text[parent_start:parent_end],
                "char_start": parent_start,
            }
        pieces = recursive_split(text, (parent_start, parent_end), chunk_tokens, SEPARATORS)
        for span in merge_small_pieces(text, pieces, chunk_tokens, overlap_tokens):
            start, end = trim(text, span)
            if start < end:
                children.append(
                    Chunk(
                        text=text[start:end],
                        source=source,
                        chunk_number=len(children),
                        strategy="parent_child",
                        char_start=start,
                        parent_id=parent_id,
                    )
                )
    return children


def parents_path(collection: str) -> Path:
    return config.MANIFEST_DIR.parent / f"parents_{collection}.json"


def save_parents(parents: dict[str, dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(parents, indent=1) + "\n", encoding="utf-8")


def load_parents(path: Path) -> dict[str, dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def lift_to_parents(hits: list[dict], parents: dict[str, dict], limit: int) -> list[dict]:
    """Child hits -> parent hits, best first, each parent once, at most `limit`.

    The text becomes the parent's text: that is what the LLM will read, so the eval must
    score it (plan 2.6.3). Score and order come from the best child of each parent.
    """
    lifted: list[dict] = []
    seen: set[str] = set()
    for hit in hits:
        parent_id = hit["parent_id"]
        if parent_id in seen:
            continue
        seen.add(parent_id)
        parent = parents[parent_id]
        lifted.append({**hit, "text": parent["text"], "child_text": hit["text"]})
        if len(lifted) == limit:
            break
    return lifted

"""Sparse (keyword) vectors with BM25, via FastEmbed (step 3.2, D-052).

Same formula as labs/lab3_bm25.py, split in two halves:
- here: the term-frequency part (with k1 = 1.2, b = 0.75 and the corpus' average length);
- in Qdrant: the IDF (rarity) part, computed over the whole collection
  (sparse vector config with modifier=IDF, store/qdrant_store.py).

A sparse vector is {word id: weight} for the few words a chunk contains: almost every slot
of the huge vocabulary is zero, so only the non-zero ones are stored.
FastEmbed's text rules (checked on fastembed 0.8.1): punctuation becomes spaces but "_"
stays ("max_length" is one word), English stop words are dropped, words are stemmed
("validated" and "validate" both become "valid"). The "model" is 90 KB of word lists.
"""

from functools import lru_cache

from fastembed import SparseTextEmbedding
from fastembed.sparse.bm25 import remove_non_alphanumeric

from docpilot import config

SPARSE_MODEL = "Qdrant/bm25"
BM25_K1 = 1.2  # saturation (FastEmbed's default; same as the lab)
BM25_B = 0.75  # length penalty (same)
# Only used before the corpus average is known; ingest measures the real one.
DEFAULT_AVG_LEN = 256.0
# Inside the project (gitignored .cache/), not the system temp folder Windows may empty.
CACHE_DIR = config.PROJECT_ROOT / ".cache" / "fastembed"


@lru_cache(maxsize=4)
def get_bm25(avg_len: float = DEFAULT_AVG_LEN) -> SparseTextEmbedding:
    """Load once per average length (it changes the document weights, not the query).

    BM25_MODEL_PATH (set in the Docker image, D-064): load the word lists from that folder
    and never check the internet. Needed because fastembed 0.8.1's "already downloaded?"
    check wants mock.file and tamil.txt, which the Qdrant/bm25 repo does not have: with no
    internet (HF_HUB_OFFLINE=1) it failed even though every needed file was cached
    (found 2026-10-23 by starting the image with --network none).
    """
    return SparseTextEmbedding(
        model_name=SPARSE_MODEL,
        cache_dir=str(CACHE_DIR),
        k=BM25_K1,
        b=BM25_B,
        avg_len=avg_len,
        specific_model_path=config.BM25_MODEL_PATH or None,  # "" on the laptop = normal
    )


def bm25_length(text: str) -> int:
    """How many words BM25 counts in `text`, after removing stop words.

    Uses FastEmbed's own steps (two of them private, pinned by fastembed==0.8.1 and checked
    by a test), so our average length is measured in exactly BM25's units.
    """
    model = get_bm25().model
    return len(model._stem(model.tokenizer.tokenize(remove_non_alphanumeric(text))))


def average_length(texts: list[str]) -> float:
    """The corpus' average length in BM25 words: the `avg_len` the length penalty needs."""
    return sum(bm25_length(text) for text in texts) / len(texts)


def to_dict(embedding) -> dict[str, list]:
    """FastEmbed result -> plain lists, so callers never depend on FastEmbed's types."""
    return {"indices": embedding.indices.tolist(), "values": embedding.values.tolist()}


def embed_sparse_documents(texts: list[str], avg_len: float) -> list[dict[str, list]]:
    """One sparse vector per chunk: word ids and their BM25 term-frequency weights."""
    return [to_dict(embedding) for embedding in get_bm25(avg_len).embed(texts)]


def embed_sparse_query(text: str) -> dict[str, list]:
    """The question's word ids, each with weight 1 (BM25 counts a question word once)."""
    return to_dict(next(iter(get_bm25().query_embed(text))))

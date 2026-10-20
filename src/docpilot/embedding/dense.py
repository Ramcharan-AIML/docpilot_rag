"""Turn text into vectors with a local sentence-transformers model (D-002)."""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from docpilot import config


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Load the model the first time it is needed, then reuse it (loading takes seconds)."""
    # revision pins the exact model files, same as the labs: the model can never change
    # under us. First run downloads about 130 MB into the Hugging Face cache.
    return SentenceTransformer(config.EMBEDDING_MODEL, revision=config.EMBEDDING_REVISION)


def embed_documents(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Embed chunks for storage. No query prefix here: documents are not questions."""
    if not texts:
        return []  # nothing to do; also avoids loading the model for nothing
    vectors = get_model().encode(
        texts,
        batch_size=batch_size,  # 32 at a time keeps memory use steady on CPU
        normalize_embeddings=True,  # length 1, so dot product == cosine similarity
        show_progress_bar=True,
    )
    return vectors.tolist()  # numpy array -> plain lists, which Qdrant accepts


def embed_query(question: str) -> list[float]:
    """Embed one question for search, with the BGE instruction prefix.

    We add the prefix by hand on purpose. The model's built-in "query" prompt is an empty
    string (checked 2026-10-12), so model.encode_query() would silently skip it.
    """
    vector = get_model().encode(config.BGE_QUERY_PREFIX + question, normalize_embeddings=True)
    return vector.tolist()

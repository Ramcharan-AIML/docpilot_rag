"""Lab 2: keyword search (shared words) vs meaning search (embeddings) on tiny examples.

Run (with the venv active):  python labs/lab2_keyword_vs_meaning.py

Before running, predict for EACH question: which document will keyword search pick,
and which will meaning search pick? Will either method fail?
"""

import re

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"  # decision D-002
MODEL_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"  # same pinned files as Lab 1

# BGE was trained with this instruction in front of QUESTIONS only (never documents).
# Checked on the model card on 2026-10-07 (decision D-002).
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

DOCUMENTS = [
    "Use Query(max_length=50) to limit the length of a query parameter.",
    "Pydantic validates the request body and returns errors automatically.",
    "Docker images are built from a Dockerfile.",
]

QUESTIONS = [
    "what does max_length do",  # an exact name from the docs
    "how do I check incoming data is correct",  # same idea as document 2, different words
]


def words(text: str) -> set[str]:
    """Lowercase words. Keeps letters, digits and '_' together, so 'max_length' stays whole
    and 'Dockerfile.' becomes 'dockerfile' (punctuation dropped)."""
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


def keyword_score(question: str, document: str) -> int:
    """Count shared words. A crude version of BM25: every word counts the same,
    so common words like 'do' count as much as rare names like 'max_length'."""
    return len(words(question) & words(document))


def best_index(scores: list[float]) -> int | None:
    """Position of the highest score, or None if every score is the same (no winner)."""
    if max(scores) == min(scores):
        return None
    return scores.index(max(scores))


def main() -> None:
    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION)
    # Vectors already come out with length 1 (Lab 1), so dot product == cosine similarity.
    doc_vectors = model.encode(DOCUMENTS, normalize_embeddings=True)

    for question in QUESTIONS:
        with_prefix = model.encode(QUERY_PREFIX + question, normalize_embeddings=True)
        without_prefix = model.encode(question, normalize_embeddings=True)

        keyword_scores = [keyword_score(question, doc) for doc in DOCUMENTS]
        meaning_scores = [float(np.dot(with_prefix, vec)) for vec in doc_vectors]
        no_prefix_scores = [float(np.dot(without_prefix, vec)) for vec in doc_vectors]

        print(f"\nQUESTION: {question}")
        print("  keyword | meaning | meaning (no prefix) | document")
        for i, doc in enumerate(DOCUMENTS):
            print(
                f"  {keyword_scores[i]:>7} | {meaning_scores[i]:>7.3f} | "
                f"{no_prefix_scores[i]:>19.3f} | {doc[:55]}"
            )

        for method, scores in [("keyword", keyword_scores), ("meaning", meaning_scores)]:
            winner = best_index(scores)
            if winner is None:
                print(f"  {method:>7} picks: NOTHING (all scores tied, no winner)")
            else:
                print(f"  {method:>7} picks: document {winner + 1}")


if __name__ == "__main__":
    main()

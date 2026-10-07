"""Lab 1: what is an embedding, and what does cosine similarity measure?

Run (with the venv active):  python labs/lab1_embeddings.py

Before running, predict: which pair of sentences will score highest, and which lowest?
"""

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"  # decision D-002
# Model files are dependencies too. Pinning the exact revision (a git commit on
# Hugging Face) means the model can never change under us, like the lock file.
# Checked on the model card on 2026-10-07.
MODEL_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """How much two vectors point the same way. 1.0 = same direction, 0 = unrelated."""
    # Written by hand on purpose, so you can see the formula:
    # cosine = (a . b) / (length of a * length of b)
    dot = float(np.dot(a, b))
    length_a = float(np.linalg.norm(a))
    length_b = float(np.linalg.norm(b))
    return dot / (length_a * length_b)


def main() -> None:
    # First run downloads the model (~130 MB) into the Hugging Face cache; later runs reuse it.
    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION)

    sentences = [
        "How do I validate incoming request data?",
        "Pydantic models check the request body for you.",
        "My cat likes to sleep in the sun.",
    ]
    vectors = model.encode(sentences)  # one vector (a row of numbers) per sentence

    print("number of vectors:", len(vectors))
    print("vector size:", len(vectors[0]))
    print("first 5 numbers of vector 0:", np.round(vectors[0][:5], 4))
    # Look at this number carefully, then read the note at the bottom of this file.
    print("length of vector 0:", round(float(np.linalg.norm(vectors[0])), 4))

    print("\ncosine similarity for every pair:")
    for i in range(len(sentences)):
        for j in range(i + 1, len(sentences)):
            score = cosine_similarity(vectors[i], vectors[j])
            print(f"  {score:.3f}  |  {sentences[i]}  <->  {sentences[j]}")


if __name__ == "__main__":
    main()

# Note on "length of vector 0":
# bge-small's last processing step is a "Normalize" module (see modules.json on the model
# card), so every vector already has length 1. When both lengths are 1, the cosine formula
# divides by 1 * 1, so cosine similarity == plain dot product. That is why later code can
# use a fast dot product, and why we tell Qdrant to use cosine distance.

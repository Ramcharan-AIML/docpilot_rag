"""Lab 3: BM25 by hand on 5 sentences (step 3.2, raw first, then the library).

Run (with the venv active):  python labs/lab3_bm25.py

Before running, predict:
1. Which word gets the LOWEST IDF (rarity score), and which the highest?
2. Question 1 "what does max_length do": which sentence wins, and is it close?
3. Question 2 "query parameter": sentence 2 is short, sentence 5 is long and says
   "query" and "parameter" more often. Which one wins?
4. Saturation table: a word repeated 10 times. Is its score 10x the score of once?

No new dependency: plain Python and math. Teaching: docs/teaching/phase_3_retrieval.md part 2.
"""

import math
import re
from collections import Counter

SENTENCES = [
    "Use Query(max_length=50) to limit the length of a query parameter.",
    "A query parameter is a key value pair after the question mark in the URL.",
    "The body of the request is validated by Pydantic.",
    "Docker builds an image from a Dockerfile and runs it as a container.",
    "Query parameters, path parameters and body parameters are all parameters: FastAPI "
    "reads the query, the path and the body of the request and checks every parameter "
    "of the request against its type.",
]

QUESTIONS = [
    "what does max_length do",  # a rare, exact name
    "query parameter",  # common words: who wins, short sentence 2 or long sentence 5?
    "how do I validate the request body",
]

# The two BM25 knobs, at their common default values.
K1 = 1.2  # how fast a repeated word stops adding score (saturation)
B = 0.75  # how much a long sentence is penalised (0 = never, 1 = fully)


def words(text: str) -> list[str]:
    """Lowercase words, in order, WITH repeats (BM25 needs counts).

    Same rule as Lab 2: letters, digits and '_' stay together, so 'max_length' is one word.
    """
    return re.findall(r"[a-z0-9_]+", text.lower())


def idf(word: str, documents: list[list[str]]) -> float:
    """How rare `word` is: big for rare words, near 0 for words in almost every document.

    n = number of documents containing the word, N = all documents. The +0.5 avoids
    dividing by zero; the +1 inside the log keeps the result above 0 (Lucene's version).
    """
    n = sum(word in document for document in documents)
    total = len(documents)
    return math.log((total - n + 0.5) / (n + 0.5) + 1)


def term_score(tf: int, length: int, average_length: float) -> float:
    """The tf part of BM25: grows with tf, but saturates; long documents get less."""
    length_penalty = 1 - B + B * length / average_length  # = 1 for an average length
    return tf * (K1 + 1) / (tf + K1 * length_penalty)


def bm25(question: str, documents: list[list[str]]) -> list[float]:
    """One BM25 score per document: the sum over question words of IDF x term score."""
    average_length = sum(len(document) for document in documents) / len(documents)
    scores = []
    for document in documents:
        counts = Counter(document)
        score = 0.0
        for word in set(words(question)):  # each question word counts once
            if counts[word]:
                score += idf(word, documents) * term_score(
                    counts[word], len(document), average_length
                )
        scores.append(score)
    return scores


def main() -> None:
    documents = [words(sentence) for sentence in SENTENCES]
    average_length = sum(len(document) for document in documents) / len(documents)

    print("Sentences (length in words):")
    for number, (sentence, document) in enumerate(zip(SENTENCES, documents, strict=True), start=1):
        print(f"  {number}. ({len(document):2} words) {sentence}")
    print(f"  average length: {average_length:.1f} words")

    vocabulary = sorted({word for document in documents for word in document})
    ranked = sorted(vocabulary, key=lambda word: idf(word, documents))
    print("\nIDF, rarest words get the most (lowest 5 and highest 5 of the vocabulary):")
    for word in ranked[:5] + ["..."] + ranked[-5:]:
        if word == "...":
            print("  ...")
            continue
        n = sum(word in document for document in documents)
        print(f"  {word:12} in {n} of {len(documents)} sentences  IDF {idf(word, documents):.3f}")

    for question in QUESTIONS:
        scores = bm25(question, documents)
        best = max(range(len(scores)), key=lambda index: scores[index])
        print(f"\nQ: {question!r}  (question words: {sorted(set(words(question)))})")
        for number, score in enumerate(scores, start=1):
            marker = "  <- best" if number - 1 == best else ""
            print(f"  sentence {number}: {score:6.3f}{marker}")

    print("\nSaturation: term score of ONE word repeated tf times (average-length sentence):")
    for tf in (1, 2, 3, 5, 10):
        score = term_score(tf, round(average_length), average_length)
        print(f"  tf={tf:2}: {score:.3f}")
    print(f"  the ceiling is k1 + 1 = {K1 + 1}: repeating a word can never beat that")


if __name__ == "__main__":
    main()

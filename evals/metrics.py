"""Retrieval metrics and a percentile, written by hand (raw first, libraries later).

Input for the retrieval metrics: a 0/1 relevance list in rank order, e.g. [0, 1, 0, 0]
means "the 2nd chunk was relevant". Averaged over questions they give the reported scores.
"""

import math


def recall_at_k(relevance: list[int], k: int) -> float:
    """Hit rate: 1.0 if any relevant chunk is in the top k, else 0.0."""
    return 1.0 if any(relevance[:k]) else 0.0


def strict_recall_at_k(relevance: list[int], k: int, num_evidence: int) -> float:
    """Share of gold snippets found in the top k (matters for multi-evidence questions)."""
    return sum(relevance[:k]) / num_evidence if num_evidence else 0.0


def reciprocal_rank(relevance: list[int]) -> float:
    """1 / rank of the first relevant chunk; 0 if none. Averaged over questions = MRR."""
    for rank, is_relevant in enumerate(relevance, start=1):
        if is_relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(relevance: list[int], k: int, num_evidence: int) -> float:
    """Rewards relevant chunks near the top. log2(rank + 1) is the 'discount'.

    DCG adds 1/log2(rank+1) for each relevant chunk; the ideal DCG puts all gold snippets
    at ranks 1, 2, ...; nDCG = DCG / ideal, so 1.0 means "perfect order".
    """
    dcg = 0.0
    for rank, is_relevant in enumerate(relevance[:k], start=1):
        dcg += is_relevant / math.log2(rank + 1)
    ideal_hits = min(num_evidence, k)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / ideal if ideal > 0 else 0.0


def mean(values: list[float]) -> float:
    """Plain average; 0.0 for an empty list so a missing type does not crash a report."""
    return sum(values) / len(values) if values else 0.0


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile: the smallest value with at least p% of values <= it.

    Chosen because the answer is always a REAL measured value (no interpolation).
    Example: 20 values, p95 -> the 19th smallest. With small n, p95 is close to the max.
    """
    if not values:
        raise ValueError("percentile of an empty list")
    ordered = sorted(values)
    rank = math.ceil(p / 100 * len(ordered))  # 1-based rank
    return ordered[max(rank, 1) - 1]

"""Reciprocal Rank Fusion (RRF): merge ranked lists using ranks only, not scores (step 3.3)."""

DEFAULT_RRF_K = 60  # the common default (Cormack et al. 2009); we also try one other value


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]], k: int = DEFAULT_RRF_K
) -> list[tuple[str, float]]:
    """Each list holds ids, best first. Returns (id, fused_score), best first.

    Why ranks and not scores: cosine scores (-1..1) and BM25 scores (0..any number) are on
    different scales. Ranks are always comparable.
    A bigger k flattens the advantage of rank 1; a smaller k sharpens it.
    Ties keep first-seen order (Python's sort is stable), so the first list wins a tie.
    """
    if k <= 0:
        raise ValueError(f"k must be positive, got {k}")
    fused: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, item_id in enumerate(ranked, start=1):
            fused[item_id] = fused.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda item: item[1], reverse=True)

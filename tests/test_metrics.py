"""Hand-computed checks of the metric formulas. These numbers are maths facts about the
formulas (worked on paper first), not DocPilot results."""

import math

import pytest

from evals.metrics import (
    mean,
    ndcg_at_k,
    percentile,
    recall_at_k,
    reciprocal_rank,
    strict_recall_at_k,
)


def test_recall_at_k_first_hit_at_rank_2():
    relevance = [0, 1, 0, 0]
    assert recall_at_k(relevance, 1) == 0.0  # rank 1 is a miss
    assert recall_at_k(relevance, 2) == 1.0  # rank 2 is inside the top 2


def test_recall_with_no_hits_is_zero():
    assert recall_at_k([0, 0, 0], 3) == 0.0


def test_reciprocal_rank():
    assert reciprocal_rank([1, 0, 0]) == 1.0  # 1/1
    assert reciprocal_rank([0, 1, 0, 0]) == 0.5  # 1/2
    assert reciprocal_rank([0, 0, 1]) == pytest.approx(1 / 3)
    assert reciprocal_rank([0, 0, 0]) == 0.0  # never found


def test_mrr_of_three_questions():
    # Same toy example as primer_evals.md: (1 + 1/3 + 0) / 3 = 0.444...
    ranks = [reciprocal_rank(r) for r in ([1, 0, 0], [0, 0, 1], [0, 0, 0])]
    assert mean(ranks) == pytest.approx(4 / 9)


def test_strict_recall_counts_each_snippet():
    # 3 gold snippets, 2 of them in the top 5 -> 2/3
    assert strict_recall_at_k([1, 0, 1, 0, 0], 5, 3) == pytest.approx(2 / 3)
    assert strict_recall_at_k([1, 0, 1], 1, 3) == pytest.approx(1 / 3)  # only rank 1 counts


def test_ndcg_single_snippet_at_rank_2():
    # DCG = 1/log2(3) = 0.6309; ideal (hit at rank 1) = 1/log2(2) = 1 -> 0.6309
    assert ndcg_at_k([0, 1, 0, 0], 5, 1) == pytest.approx(1 / math.log2(3))


def test_ndcg_perfect_order_is_one():
    assert ndcg_at_k([1, 1, 0], 5, 2) == pytest.approx(1.0)


def test_ndcg_two_snippets_only_one_found_at_rank_3():
    # DCG = 1/log2(4) = 0.5; ideal = 1 + 1/log2(3) = 1.6309 -> 0.3066
    assert ndcg_at_k([0, 0, 1], 5, 2) == pytest.approx(0.5 / (1 + 1 / math.log2(3)))


def test_ndcg_ignores_hits_after_k():
    assert ndcg_at_k([0, 0, 0, 0, 0, 1], 5, 1) == 0.0


def test_percentile_nearest_rank():
    values = [40, 10, 30, 20]  # unsorted on purpose
    assert percentile(values, 50) == 20  # rank ceil(0.5*4) = 2 -> 2nd smallest
    assert percentile(values, 95) == 40  # rank ceil(0.95*4) = 4 -> the largest
    assert percentile(list(range(1, 21)), 95) == 19  # rank ceil(19.0) = 19


def test_percentile_of_empty_list_fails_loudly():
    with pytest.raises(ValueError):
        percentile([], 50)

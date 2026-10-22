Continues from [3_USER_GUIDE.md](3_USER_GUIDE.md)

# DocPilot User Guide (part 4)

---

## 48. Step 3.3: hybrid search, two searchers vote with RRF (2026-10-22)

**Idea:** ask the meaning searcher and the keyword searcher for their top 50 each, then
merge the two lists by **rank** (Reciprocal Rank Fusion: each list gives a chunk
1/(60 + rank) points). Ranks, not scores, because cosine and BM25 scores use different scales.

| Searcher (FT-200 chunks, dev n=41) | R@1 | R@3 | R@5 | MRR | search p50 |
|---|---|---|---|---|---|
| Meaning only (dense) | **0.634** | 0.732 | 0.805 | **0.701** | 9.9 ms |
| Keywords only (sparse) | 0.537 | 0.683 | 0.805 | 0.658 | 14.0 ms |
| Hybrid, RRF k=60 (C6) | 0.585 | **0.805** | **0.829** | 0.699 | 24.8 ms |

- Hybrid finds the answer in the **top 3 for 3 more questions** and the top 5 for 1 more,
  but has it at **rank 1 for 2 fewer**. More right chunks near the top, but not in the right order.
- It did **not** reach the 36/41 ceiling: chunks only BM25 liked (q-010, q-018, q-048) got
  one vote and landed at ranks 6-7. RRF rewards **agreement**.
- k=10 was 1 question worse than k=60: noise level, so we keep the default 60.
- Next: 3.4 does the same fusion inside Qdrant (one call); 3.5's reranker re-orders the
  candidates, which is where the rank-1 loss should come back.

---

## 49. Step 3.4: let Qdrant do the mixing (2026-10-22)

**Before (3.3):** our code asked Qdrant twice (meaning, then keywords) and mixed the two
lists itself. **Now (3.4):** one request; Qdrant searches both ways and mixes inside.

| | Our code (C6-k60) | Qdrant (C6-server) |
|---|---|---|
| Trips to Qdrant | 2 | 1 |
| Recall@5 | 0.829 | 0.829 |
| Recall@1 | 0.585 | 0.561 (one tie, see below) |
| Search time p50 | 24.8 ms | **12.3 ms** |

- **Same answers:** on 10 questions, both gave the same top 5 in the same order (10/10).
- **The k trap:** Qdrant's formula is 1/(k + rank - 1), so we send k = 61 to match our 60.
  Qdrant's default k is 2: with it, only 2 of 10 had the same order.
- **Ties:** when two chunks have exactly the same score, Qdrant picks the order at random
  (30 tries: 16 one way, 14 the other). Our code always puts the meaning-search one first.
  One such tie (q-055) was at rank 1, so Recall@1 moved by 1 question. Not a real loss.
- **Decision:** Qdrant's version is the default (same results, half the time).

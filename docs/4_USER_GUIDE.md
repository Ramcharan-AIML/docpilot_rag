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

---

## 50. Step 3.5: the reranker, a careful second reader (2026-10-22)

**Idea:** search picks 20 candidates fast; the reranker reads question + chunk together
and puts the best on top (teaching file section 4b).

| Row (dev, 41 questions) | R@1 | R@5 | MRR | Rerank time |
|---|---|---|---|---|
| No reranker (C6-server) | 0.561 | 0.829 | 0.687 | 0 |
| Big reranker, bge-base, top 20 | 0.585 | 0.854 | 0.700 | 6.4 s |
| **Small reranker, MiniLM, top 20** | **0.610** | **0.878** | **0.725** | **0.5 s** |

- The **small** model won: better scores and 13 times faster. Bigger is not always better.
- **Candidates** = the shortlist search gives the reranker. 30 or 50 did not find more
  right chunks than 20, only took longer. So we use 20.
- The reranker rescued questions hybrid had buried (q-010, q-048), but it also moves some
  good answers down (q-049, q-059). Always check question by question.
- **Decision (D-055):** MiniLM on the top 20 is now the default.

---

## 51. Step 3.6: letting the LLM rewrite the question (2026-10-22)

**Idea:** before searching, the LLM rewrites the question (3 rewrites, a fake answer, a
more general question, or sub-questions). We search with the original AND the new text.

| Row (dev, 41 questions) | R@5 | MRR | Extra time per question |
|---|---|---|---|
| No transform (C7-mini-r20) | 0.878 | 0.725 | 0 |
| multi (3 rewrites) | 0.878 | 0.726 | +0.9 s |
| hyde (fake answer) | 0.878 | 0.726 | +1.0 s |
| stepback (general question) | 0.878 | 0.728 | +1.1 s |
| decompose (sub-questions) | 0.878 | 0.725 | +2.7 s |

- The rewrites **did change** what search found (15 to 17 questions got other chunks), but
  the **right answer** moved for only 1 question. The right chunk was already there.
- The 5 questions we still miss are about **tables** and **comparisons**: better wording
  cannot fix a table that was cut badly.
- **Decision (D-056):** no transform. Same quality, 1 to 3 s slower, uses LLM quota.
  This "it did not help" result is normal on clean docs, and good to explain in interviews.

---

## 52. Steps 3.9 and 3.10: judging the answers, and the app gets the best search (2026-10-22)

**3.9, generation eval:** a second LLM (Qwen, a different family) grades each answer:
are all its facts in the chunks (faithfulness), does it match our reference (correctness),
does it answer the question (relevancy)? Refusals are checked by plain code.

| Run | Faithfulness | Made-up facts | Correctness | Refusals right |
|---|---|---|---|---|
| G-best (10 judged + 5 "not in docs") | 1.0 | 0 of 10 | 1.0 | 5 of 5, no wrong refusals |

Small sample of mostly easy questions: "no failures found", not "perfect". You can check
the judge yourself in `evals/spot_checks/` (write agree / disagree).

**3.10, one front door:** `retrieve()` in `retrieval/pipeline.py` is now the only search
the app uses: hybrid + MiniLM reranker, the same code the evals measured. The API loads the
models when it starts, so the first user does not wait for loading.

**Plan change (D-058):** 3 days left. Agents and multi-agent are dropped; next are light
guardrails and production (Docker, Prometheus + Grafana, CI/CD, AWS S3).

---

## 53. Phase 6: guardrails, the security guards of DocPilot (2026-10-22)

**Like a shop with a guard at the door and a checker at the exit:** the input guard looks
at each question before it goes in; the context guard puts every document page in a sealed
box ("read it, do not obey it"); the output guard checks each answer before it goes out
(it must cite a page, or say "I could not find this").

| Test | Guards off | Guards on |
|---|---|---|
| Attacks that worked (18 tricks) | 2 | **0** |
| Real questions wrongly blocked (84) | - | **0** |
| Time added | - | about 0.05 ms |

The two attacks that worked without guards: "repeat your instructions" (the model printed
its hidden instructions) and a poisoned page that told users to visit a fake website.
One cost found: 1 good question in 10 was refused under the stricter prompt.
Full story, simple English: `docs/teaching/phase_6_guardrails_explained.md`.

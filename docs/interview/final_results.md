# DocPilot: Final Results (for resume and interviews)

Every number below comes from a real run, saved in `evals/results/` and MLflow, with its
git commit in `evals/ABLATION.md`. Dev set = 41 answerable questions (1 question = 0.024).
Unknown = `n/a`. Updated 2026-10-22.

## Corpus and test set

| What | Number |
|---|---|
| Documents | 20 (FastAPI, Pydantic, Docker docs; Chain-of-Thought PDF; 3 Wikipedia articles; own interview notes as DOCX) |
| Chunks (FT-200: 200 tokens, overlap 25) | 453 |
| Golden questions (v1) | 65 (dev 46, test 17, plus a 7-question CI set) |
| Chunking configurations compared | 11 |
| Automated tests | 201 |

## Retrieval: from baseline to final (dev, n=41)

| Stage | R@1 | R@3 | R@5 | MRR | nDCG@5 |
|---|---|---|---|---|---|
| Baseline C0 (800-char chunks, dense) | 0.537 | 0.756 | 0.780 | 0.650 | 0.659 |
| + better chunking FT-200 (dense) | 0.634 | 0.732 | 0.805 | 0.701 | 0.722 |
| + hybrid BM25 + dense, RRF in Qdrant | 0.561 | 0.805 | 0.829 | 0.687 | 0.715 |
| **+ MiniLM cross-encoder reranker (final)** | **0.610** | **0.829** | **0.878** | **0.725** | **0.762** |

Headline: **Recall@5 0.78 -> 0.88, MRR 0.65 -> 0.73** (baseline -> final, dev).
**Held-out test split (n=17, never used for any choice):**

| Stage | R@1 | R@5 | MRR | nDCG@5 |
|---|---|---|---|---|
| Baseline C0 | 0.353 | 0.941 | 0.608 | 0.674 |
| FT-200 (dense) | 0.471 | 0.882 | 0.620 | 0.657 |
| **Final (hybrid + reranker)** | **0.647** | **0.941** | **0.765** | **0.790** |

Test headline: **top-1 accuracy 0.35 -> 0.65, MRR 0.61 -> 0.77** (`c1fb7dd`).

## Generation (LLM judge, step 3.9)

Generator `openai/gpt-oss-120b` (Groq), judge `qwen/qwen3.8-27b` (different family).

| Metric | Result |
|---|---|
| Faithfulness (facts supported by the retrieved chunks) | 1.0 on 10 judged answers |
| Hallucination rate | 0 of 10 |
| Correctness vs human reference | 1.0 |
| Abstention ("not in the documents") | 5 of 5 correct, 0 false refusals |
| Phase 1 abstention accuracy (golden v0) | 0.91, zero fabricated answers |

Small sample: "no failures found", not "perfect".

## Latency (laptop CPU, warm)

| Stage | p50 | Note |
|---|---|---|
| Qdrant search (Docker, dense) | 7.6 ms | was 2,062 ms via `localhost` (Windows IPv6 trap), fixed with 127.0.0.1 |
| Hybrid search in Qdrant (one call) | 12.3 ms | hand-written RRF in Python: 24.8 ms |
| Reranker, 20 candidates | MiniLM 485 ms | bge-reranker-base: 6,430 ms for 1 question less at R@5: rejected |
| LLM answer | 990 ms | Groq free tier |
| End-to-end, final pipeline | n/a | to be measured with Prometheus (one sample: 2.7 s) |
| End-to-end, Phase 1 app | 1.1 s | dense only, no reranker |

## Experiments that did NOT help (honest, good interview stories)

| Experiment | Result |
|---|---|
| 4 query transforms (multi-query, HyDE, step-back, decomposition) | all R@5 0.878 = no gain, +0.9 to 2.7 s each: none kept |
| Bigger reranker (1.1 GB) vs small (91 MB) | small was better AND 13x faster |
| Rerank 30 or 50 candidates instead of 20 | no new right chunks, slower |
| RRF k = 10 vs 60 | 1 question worse: kept 60 |

## Engineering

- CI eval gate in GitHub Actions: an injected chunking-units bug dropped MRR 0.87 -> 0.50
  and the build failed.
- All model files pinned to exact revisions; every metric traceable to a git commit.

## Copy-ready resume lines (evals, true on 2026-10-22)

1. Built an evaluation-driven RAG pipeline over 20 technical documents (453 chunks) with a
   65-question golden set (dev/test split, verbatim evidence) and hand-written Recall@k, MRR
   and nDCG metrics; every run tracked in MLflow and traceable to a git commit.
2. Raised retrieval quality from **Recall@5 0.78 to 0.88** and **MRR 0.65 to 0.73** (dev)
   through an 11-configuration chunking ablation, hybrid BM25 + dense search with Reciprocal
   Rank Fusion in Qdrant, and a cross-encoder reranker; on a held-out test set, **top-1
   accuracy rose from 0.35 to 0.65 and MRR from 0.61 to 0.77**.
3. Benchmarked rerankers on CPU and chose a 91 MB MiniLM cross-encoder over a 1.1 GB model
   that was 13x slower (6.4 s vs 0.49 s per query) and scored lower; showed that 4 query
   transforms (HyDE, multi-query, step-back, decomposition) added 0.9-2.7 s with no recall
   gain, and left them out.
4. Built an **LLM-as-a-judge generation eval** (Qwen judging GPT-OSS answers: claim-level
   faithfulness, correctness, relevancy, with human spot-check files): **faithfulness 1.0
   and zero hallucinated claims** on 10 judged answers, and **5/5 correct refusals** on
   out-of-scope questions (0.91 abstention accuracy at baseline).
5. Added a **CI eval gate** in GitHub Actions that fails pull requests when retrieval drops
   (caught an injected bug: MRR 0.87 to 0.50), and measured per-stage latency (p50: hybrid
   search 12 ms, reranker 0.49 s, LLM 0.99 s).

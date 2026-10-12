# Phase 8: Stretch Goals (Implementation Plan, optional)

**Rule:** nothing here starts before the Phase 7 gate passes. Each item is a small
experiment with its own ablation row. Pick one or two, not all.

**Teaching companion:** `docs/teaching/phase_8_stretch.md`

| # | Item | Files | What to measure | Cost / risk |
|---|---|---|---|---|
| 8.1 | GraphRAG-lite | `retrieval/graph_expand.py`, `ingestion/crossrefs.py` | Multi-hop question Recall@5 with and without graph expansion | Low: graph built from explicit links, no LLM |
| 8.2 | DSPy prompt optimisation | `optim/dspy_generate.py` | Faithfulness and correctness on dev before/after; then test once | Many LLM calls: rate limits; overfitting to dev |
| 8.3 | ColBERT late interaction | `retrieval/colbert.py` | Recall/MRR vs hybrid+rerank; index size; latency | Bigger index; CPU speed |
| 8.4 | ColPali multimodal PDF | `retrieval/colpali.py` | Questions about diagrams in PDFs | Heavy model; probably too slow on CPU, so verify first |
| 8.5 | Agent trajectory evals | `evals/run_trajectory_eval.py` | Did the agent take a sensible path (not just the right final answer)? | Needs labelled expected paths |
| 8.6 | Upload your own documents (D-030) | `api/upload.py`, `ingestion/user_docs.py` | Uploaded file goes through the Phase 6 input guards and a prompt-injection scan; per-user collection; abstention and attack success on uploaded files | Main prompt-injection and copyright risk: only after the Phase 6 gate; never mixed into the public index |

---

## 8.1 GraphRAG-lite in a bit more detail

1. `ingestion/crossrefs.py`: find explicit links in docs ("see [Path Parameters](...)",
   Markdown links between pages). Each link = an edge `chunk A -> section B`.
2. Store edges in Postgres (or a JSON file): `from_chunk_id, to_source, to_heading`.
3. `retrieval/graph_expand.py`: after normal retrieval, add the top chunks of linked
   sections (max 2 extra), then rerank everything.
4. Measure on multi-hop questions only, and on the full set (must not hurt the rest).

Why not full GraphRAG (LLM extracts entities and relations from every chunk): one or more
LLM calls per chunk, rebuilt on every doc change; too costly on free tiers. Explicit links
already exist in docs and cost nothing.

## 8.2 DSPy

- VERIFY current DSPy API. Define the generate step as a DSPy module, metric = our
  faithfulness + correctness judge, optimise on **dev only**, then run **test once**.
- Danger: the optimiser can overfit to the judge. Spot-check by hand.

## 8.5 Trajectory evals

- For 20 questions, write the expected path (e.g. `router -> retrieve -> grade -> generate`).
- Compare with the trace. Report: path match rate, unnecessary rewrites, unnecessary tool
  calls. This catches agents that get the right answer by luck after wasted steps.

## Note: Kubernetes moved

k3s is now **planned** in Phase 7 (step 7.14) and EKS is a Phase 7 exercise (step 7.15),
so they are no longer stretch items (decisions D-021, D-023).

---

## Phase 8 "gate"

Each experiment you run: ablation row, decision entry (kept or dropped, with numbers),
two interview answers. Negative results are fine and worth recording.

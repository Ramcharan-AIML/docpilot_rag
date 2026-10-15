Continues from [2_USER_GUIDE.md](2_USER_GUIDE.md)

# DocPilot User Guide (part 3)

---

## 28. Phase 0 and Phase 1 gates closed (2026-10-15)

**What a gate is:** a checklist that must pass before the next phase starts. Like a school
year: you move up only after the final exam, so gaps do not pile up.

**Phase 1 gate, item by item:**
| Item | Result |
|---|---|
| Tests green | 62 passed, on Windows and on GitHub's Linux machine |
| Failure log | 10 rows + 3 summary lines |
| Golden set | 32 items, validator OK |
| C0 retrieval | dev: Recall@5 0.842, MRR 0.667, nDCG@5 0.670; test (run once): Recall@5 1.000, MRR 0.635 |
| Abstention | 0.909 (0/3 made-up answers, 2/19 wrong refusals) |
| Latency L0 | warm p50 1107 ms, p95 1764 ms (LLM about 96%) |
| Versions pinned | D-026 to D-035 |
| Interview notes | written as **mentor drafts** at your request: rewrite them in your own words |
| CI | green on PR #1; branch protection deferred until the repo is public (D-035) |
| Merge + tag | PR #1 merged into `main`; tags `phase-0` and `phase-1` |

**Honest note:** the gate asks for answers in your own words because interviews test you,
not the file. The drafts are a starting point: read one, close it, say it aloud, rewrite.

**What Phase 1 proved, in one breath:** the baseline finds the right chunk for most
questions but rarely ranks it first; the chunk text itself is broken (missing code, cut
sentences, HTML); the LLM refuses honestly; and the LLM is almost all of the waiting time.
Phase 2 fixes the chunk text and compares chunking strategies against C0.

---

## 29. Step 2.0: MLflow, the lab notebook (2026-10-15, not yet committed)

**Goal:** every eval run is recorded automatically and can be sorted and compared on a web
page. Like a scientist's lab notebook: recipe, result, and the photos stapled in.

**Files:** `evals/tracking.py`, `evals/relog_results_to_mlflow.py`,
`tests/test_tracking.py`; settings in `config.py`; decision D-036 (`mlflow==3.17.1`,
dev only).

| MLflow word | In DocPilot |
|---|---|
| experiment | `docpilot-retrieval`, `docpilot-latency`, `docpilot-abstention` |
| run | one saved result file, named by config id (C0) |
| params | the recipe: golden version, chunk strategy and size, model, split |
| metrics | the scores: recall_at_5, mrr, total_p50_ms, accuracy, ... |
| tags | config id, git commit, results file, ablation |
| artifact | the full results JSON |

**Why full MLflow, not mlflow-skinny:** skinny has no web UI and no SQLite storage.
**Why not W&B:** hosted, plan limits, data leaves the laptop.

**Run (hands-on):**
```powershell
python -m evals.relog_results_to_mlflow
mlflow ui --backend-store-uri sqlite:///mlflow.db
```
Then open `http://127.0.0.1:5000`. From now on every eval run is logged by itself.

**Real results:** smoke test (throwaway database): 4 C0 files logged, numbers equal to the
JSON, re-run skips duplicates. Your own UI check: n/a (pending).

**PDF and Word (D-037):** step 2.7 now covers PDF, Word (DOCX) and HTML with Docling.


# DocPilot Progress

Update this file at the end of every session. Newest session log entry goes on top.

---

## Right now

| Item | Value |
|---|---|
| Current phase | Phase 0 / Phase 1 setup |
| Current step | 0.4 Lab 2: keyword vs meaning search |
| Next step | Phase 0 gate (interview notes, tag `phase-0`) |
| Blockers | Section 18 of `PROJECT_DOCUMENTATION.md` says Phase 0 and Phase 1a code exist, but this repo only contains `README.md` and `docs/`. Waiting for learner: is that code somewhere else, or do we rebuild it here? |
| Homework | (1) Two own-words sentences for Lab 2 (which method got each question right, and why). (2) Answer Phase 0 questions in `interview_notes.md`. (3) Lab 1 homework: why the paraphrase (0.799) beat the Pydantic sentence (0.708) |

---

## Phase checklist

Status values: `not started`, `in progress`, `done`, `blocked`.

### Phase 0: Foundations
| Step | What | Status |
|---|---|---|
| 0.1 | Project skeleton (folders, `.gitignore`, `.env.example`) | done (commit 497a9a4) |
| 0.2 | Virtual environment, `pyproject.toml`, pinned `requirements.txt` | done (commit 497a9a4) |
| 0.3 | `labs/lab1_embeddings.py` (embeddings and cosine similarity) | done (commit 5924b95) |
| 0.4 | Lab 2: keyword vs meaning search | run done; waiting for learner's two own-words sentences |
| Gate | tag `phase-0` | not started |

### Phase 1: Naive baseline, eval harness, mini API
| Step | What | Status |
|---|---|---|
| 1a.1 | `config.py` | not started |
| 1a.2 | `loader.py` | not started |
| 1a.3 | `chunker.py` + `tests/test_chunker.py` | not started |
| 1a.4 | `embedder.py` | not started |
| 1a.5 | `vector_store.py` | not started |
| 1a.6 | `llm.py` | not started |
| 1a.7 | `rag.py` | not started |
| 1a.8 | scripts `01_download_docs.py`, `02_ingest.py`, `03_ask.py` | not started |
| 1b | Ask 10 questions, write `docs/failure_log_phase1.md` | not started |
| 1c | Golden dataset v0 (about 30 questions, dev/test) | not started |
| 1d | Retrieval eval harness, record C0 | not started |
| 1e | Mini FastAPI `POST /ask` | not started |
| Gate | tag `phase-1` | not started |

### Phase 2: Ingestion quality and chunking
| Step | What | Status |
|---|---|---|
| 2.1 | Refactor into `ingestion/` package | not started |
| 2.2 | Cleaner (HTML noise) | not started |
| 2.3 | Include resolver (`{* ... *}` markers) | not started |
| 2.4 | Block parser (code, tables, headings kept whole) | not started |
| 2.5 | Metadata (source, heading path, doc type, version, technology) | not started |
| 2.6 | Six chunking strategies | not started |
| 2.7 | Docling for PDF/HTML | not started |
| 2.8 | Add more corpora (Docker, Pydantic, ...) + grow golden set | not started |
| 2.9 | Index per strategy, run evals, per-type breakdown | not started |
| Gate | C1 to C5 rows filled, strategy chosen; tag `phase-2` | not started |

### Phase 3: Retrieval upgrade
| Step | What | Status |
|---|---|---|
| 3.1 | Docker primer; Qdrant in Docker | not started |
| 3.2 | Sparse (BM25) vectors | not started |
| 3.3 | Manual RRF | not started |
| 3.4 | Qdrant server-side fusion | not started |
| 3.5 | Reranker + CPU latency | not started |
| 3.6 | Query transforms | not started |
| 3.7 | Embedding model comparison | not started |
| 3.8 | Metadata filtering | not started |
| 3.9 | Generation eval harness v0 (faithfulness, relevancy, abstention) | not started |
| Gate | C6 to C8 rows; tag `phase-3` | not started |

### Phase 4: Agentic RAG with LangGraph
| Step | What | Status |
|---|---|---|
| 4.1 | Hand-made agent loop | not started |
| 4.2 | LangGraph primer (toy graph) | not started |
| 4.3 | State and nodes | not started |
| 4.4 | Graph with conditional edges and caps | not started |
| 4.5 | RAGAS / DeepEval integration | not started |
| 4.6 | Agentic vs non-agentic comparison | not started |
| Gate | C9 row; tag `phase-4` | not started |

### Phase 5: Multi-agent, tools, MCP, HITL
| Step | What | Status |
|---|---|---|
| 5.1 | Tools (calculator, SQL, web search, doc section) | not started |
| 5.2 | Table extraction to DuckDB/SQLite | not started |
| 5.3 | Supervisor + specialists | not started |
| 5.4 | Human-in-the-loop with persistent checkpointer | not started |
| 5.5 | Reviewer endpoints | not started |
| 5.6 | MCP server | not started |
| 5.7 | Routing and tool-call evals | not started |
| Gate | C10 row; restart demo; tag `phase-5` | not started |

### Phase 6: Guardrails and security
| Step | What | Status |
|---|---|---|
| 6.1 | Red-team set v0 | not started |
| 6.2 | Plain-Python input guards | not started |
| 6.3 | Untrusted-context handling + poisoned doc | not started |
| 6.4 | Plain-Python output guards | not started |
| 6.5 | Tool guards | not started |
| 6.6 | Presidio | not started |
| 6.7 | NeMo / Guardrails AI / Llama Guard comparison | not started |
| Gate | C11 + safety table; tag `phase-6` | not started |

### Phase 7: Production
| Step | What | Status |
|---|---|---|
| 7.1 | FastAPI hardening (async, SSE, health, logs) | not started |
| 7.2 | Auth (API keys) | not started |
| 7.3 | Redis: rate limit, exact cache, semantic cache | not started |
| 7.4 | Hand-made fallback, then LiteLLM | not started |
| 7.5 | Tracing (decide D-009) | not started |
| 7.6 | Prometheus + Grafana | not started |
| 7.7 | Dockerfile + full Compose | not started |
| 7.8 | GitHub Actions (CI, eval gate, build, deploy) | not started |
| 7.9 | Deploy to free VM with HTTPS | not started |
| 7.10 | Load test | not started |
| 7.11 | Incremental ingestion | not started |
| 7.12 | README, demo UI, big interview file | not started |
| Gate | public URL, gate proven; tag `phase-7` | not started |

### Phase 8: Stretch (optional)
Not planned until Phase 7 is done.

---

## Numbers so far

None yet. Every number will come from a real run and be copied here from
`evals/ABLATION.md`.

| Config | Recall@5 | MRR | nDCG@5 | Date | Commit |
|---|---|---|---|---|---|
| C0 | n/a | n/a | n/a | n/a | n/a |

---

## Session log

### 2026-10-08, session 5
- Recorded Lab 2 results (see session 4). Fixed stale "commit pending" for 0.1/0.2.
- Wrote `docs/USER_GUIDE.md` (story of every step so far), `CLAUDE.md` (root rules file
  Claude Code loads automatically), `docs/CHAT_CONTEXT.md` (handoff for a new chat).
  Linked them in `docs/README.md`.

### 2026-10-08, session 4
- Step 0.4: wrote `labs/lab2_keyword_vs_meaning.py` (plan version + regex word splitting so
  punctuation does not block matches, a "picks" line per method, and a meaning-without-prefix
  column). Ruff clean; helper functions tested on made-up text; model loads.
- Real questions deliberately not run, so the learner predicts first.
- Learner's predictions (written before running):
  Q1 "what does max_length do": keyword -> doc 1, meaning -> doc 1.
  Q2 "how do I check incoming data is correct": keyword -> no match in any doc,
  meaning -> doc 2. Prefix bonus: no prediction.
- Learner's real Lab 2 run (bge-small, revision 5c38ec7c, CPU):
  | Question | Doc | keyword | meaning (prefix) | meaning (no prefix) |
  |---|---|---|---|---|
  | Q1 max_length | 1 Query(max_length) | 1 | **0.742** | 0.775 |
  | Q1 | 2 Pydantic | 0 | 0.539 | 0.592 |
  | Q1 | 3 Docker | 0 | 0.490 | 0.534 |
  | Q2 check data | 1 Query(max_length) | 0 | 0.578 | 0.564 |
  | Q2 | 2 Pydantic | 0 | **0.659** | 0.670 |
  | Q2 | 3 Docker | 0 | 0.502 | 0.529 |
  Picks: Q1 keyword doc 1, meaning doc 1. Q2 keyword NOTHING (all tied at 0), meaning doc 2.
- All four predictions correct.
- Findings: (a) keyword search failed Q2 completely: zero shared words with any doc;
  (b) meaning search got both; Q1 margin 0.742 vs 0.539, Q2 margin only 0.659 vs 0.578;
  (c) the prefix lowered 5 of 6 scores and changed no winner; it widened the Q1 gap
  (0.203 vs 0.183) but narrowed the Q2 gap (0.081 vs 0.106). Two questions cannot show
  whether the prefix helps: that needs the Phase 1 eval set.
- Honest limit: this lab did NOT show meaning search failing. Q1 (an exact name) was won by
  both methods. A harder test (e.g. max_length vs min_length docs) would be needed; real
  evidence comes from per-type evals in Phase 3 (hybrid search).

### 2026-10-07, session 3
- Step 0.3: verified the bge-small model card (384 dims, 512-token limit, MIT, query prefix,
  built-in Normalize module); recorded in D-002 with pinned revision.
- Wrote `labs/lab1_embeddings.py` (plan version + vector length printout + pinned revision).
- Smoke test: ruff clean; cosine function correct on known vectors (1, 0, -1, with tiny
  floating-point error); model downloads and returns 384 numbers. Pair scores deliberately
  not run, so the learner predicts first.
- Learner's real Lab 1 run (bge-small, revision 5c38ec7c, CPU): vector size 384, length of
  vector 0 = 1.0. Cosine: validate-request vs Pydantic-body **0.708**; validate-request vs
  cat **0.379**; Pydantic-body vs cat **0.388**.
- Learner predicted: highest pair, lowest pair, length 1.0 — all correct. Missing: the
  "why" for the lowest pair. Lessons noted: unrelated text still scores ~0.38 (scores rank,
  they are not percentages); 0.379 vs 0.388 is a tie, not a winner.
- Break-it run (sentence 2 -> "Make sure the data a client sends is correct."):
  validate-request vs paraphrase **0.799**; validate-request vs cat **0.379** (unchanged,
  same two sentences); paraphrase vs cat **0.410**. No prediction was written before this
  run. Honest note: the paraphrase still shares the word "data", so it was not a perfect
  zero-shared-words test. Lesson: a restated question scores higher than an answer-style
  sentence (0.799 vs 0.708), the reason BGE uses a query prefix (Lab 2).
- Lab file restored to the original sentences (committed version matches recorded scores).
- Step 0.3 done.

### 2026-10-03, session 2
- Docs merged into `main`; working on branch `phase-0-foundations`.
- Step 0.1 done: `.gitignore`, `.env.example` (added `LLM_MODEL`, which Phase 1 `config.py` reads),
  `src/docpilot/__init__.py`, and `.gitkeep` placeholders (git does not track empty folders).
- Verified: a test `.env` and a test file in `data/docs/` are both ignored (`git check-ignore -v`).
- Step 0.2 done: reused existing `.venv` (Python 3.13.2). Versions checked on PyPI today.
  `pyproject.toml`, `requirements.txt` (runtime), `requirements-dev.txt` (pytest, ruff),
  generated `requirements-lock.txt`. New decisions D-015 (Python 3.12+, numpy needs it) and
  D-016 (requirements split + lock). Plan docs updated from 3.11 to 3.12+/3.13.
- Verified: `import docpilot` works from another folder; torch is `2.14.1+cpu`;
  `pip check` clean; `ruff check src/` clean.

### 2026-10-03, session 1
- Read `PROJECT_DOCUMENTATION.md` fully.
- Found that the repo has no code yet, although section 18 says Phase 0 and 1a are done.
- Created the document set: rule book, progress, decisions, architecture, implementation
  plan (all phases), teaching notes (all phases), interview Q&A (all phases).
- Next: learner answers the code-location question, then step 0.1.

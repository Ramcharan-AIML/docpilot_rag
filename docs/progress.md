# DocPilot Progress

Update this file at the end of every session. Newest session log entry goes on top.

---

## Right now

| Item | Value |
|---|---|
| Current phase | Phase 1 (Phase 0 gate still open: learner's choice, 2026-10-09) |
| Current step | 1a.4 `embedder.py`: built, waiting for learner's prediction + run |
| Next step | 1a.5 `vector_store.py` (needs qdrant-client: PyPI check + decision first); Phase 0 gate (notes, tag `phase-0`) done later by the learner |
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
| 1a.1 | `config.py` (+ python-dotenv 1.2.4, D-026) | done (run 2026-10-09; not yet committed) |
| 1a.2 | `loader.py` + `tests/test_loader.py` | done (run 2026-10-10; 4 tests pass) |
| 1a.3 | `chunker.py` + `tests/test_chunker.py` | done (run 2026-10-12; 9 tests pass) |
| 1a.4 | `embedder.py` + `tests/test_embedder.py` | built, lint + tests pass; learner run pending |
| 1a.5 | `vector_store.py` | not started |
| 1a.6 | `llm.py` | not started |
| 1a.7 | `rag.py` | not started |
| 1a.8 | scripts `01_download_docs.py`, `02_ingest.py`, `03_ask.py` | not started |
| 1b | Ask 10 questions, write `docs/failure_log_phase1.md` | not started |
| 1c | Golden dataset v0 (about 30 questions, dev/test) | not started |
| 1d | Retrieval eval harness, record C0 | not started |
| 1e | Mini FastAPI `POST /ask` | not started |
| 1f | Git workflow: public repo, PR template, CI `test`, branch protection | not started |
| Gate | tag `phase-1` | not started |

### Phase 2: Ingestion quality and chunking
| Step | What | Status |
|---|---|---|
| 2.0 | MLflow tracking; re-log C0 | not started |
| 2.1 | Refactor into `ingestion/` package | not started |
| 2.2 | Cleaner (HTML noise) | not started |
| 2.3 | Include resolver (`{* ... *}` markers) | not started |
| 2.4 | Block parser (code, tables, headings kept whole) | not started |
| 2.5 | Metadata (source, heading path, doc type, version, technology) | not started |
| 2.6 | Six chunking strategies | not started |
| 2.7 | Docling for PDF/HTML | not started |
| 2.8 | Add more corpora (Docker, Pydantic, ...) + grow golden set | not started |
| 2.9 | Index per strategy, run evals, per-type breakdown | not started |
| 2.10 | CI retrieval eval gate (fixture corpus) required on `main` | not started |
| Gate | C1 to C5 rows filled, strategy chosen; tag `phase-2` | not started |

### Phase 3: Retrieval upgrade
| Step | What | Status |
|---|---|---|
| 3.1 | Docker primer; Qdrant in Docker | not started |
| 3.1b | SeaweedFS + boto3 object storage; MLflow server | not started |
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
| 7.2 | Auth (API keys) + Postgres | not started |
| 7.3 | Redis: rate limit, exact cache, semantic cache | not started |
| 7.4 | Hand-made fallback, then LiteLLM | not started |
| 7.5 | Tracing (decide D-009: Langfuse / Phoenix / MLflow) | not started |
| 7.6 | Prometheus + Grafana | not started |
| 7.7 | RAG monitoring (scores, sampled groundedness, refusals, drift, alerts) | not started |
| 7.8 | Dockerfile, multi-arch (amd64 + arm64) | not started |
| 7.9 | Full Compose stack (profiles) | not started |
| 7.10 | CI/CD: audit, terraform-check, OIDC -> ECR + GHCR, SSM deploy | not started |
| 7.11 | AWS account (record date!), safety, budgets, CLI, Terraform warm-up | not started |
| 7.12 | Terraform AWS infra (state, VPC, SG, IAM, S3, ECR, CloudWatch, EC2) | not started |
| 7.13 | First deploy on EC2 (Compose) + HTTPS | not started |
| 7.14 | k3s on EC2; production on Kubernetes | not started |
| 7.15 | EKS exercise (plan-only default; destroy same session) | not started |
| 7.16 | Load test | not started |
| 7.17 | Incremental ingestion (CronJob) | not started |
| 7.18 | Oracle module + rehearsal; move before month 6 | not started |
| 7.19 | README, demo UI, big interview file | not started |
| Gate | public URL, all infra via Terraform, gate proven; tag `phase-7` | not started |

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

### 2026-10-12, session 7d: Phase 1 step 1a.4 (embedder.py)

- 1a.3 committed by the learner (`1a80095`, `2aaca9b`). The committed `chunker.py` had a
  trailing blank line (editor), so `ruff format --check` failed; fixed with `ruff format`
  (whitespace only).
- `src/docpilot/embedder.py` + `tests/test_embedder.py` (4 tests, real model). Full suite:
  17 passed in 16.49 s (model load dominates).
- Plan bug fixed openly: no `revision=` on the model load. Checked the installed API
  (sentence-transformers 6.1.0): `encode_query()` exists but the model's stored query
  prompt is empty, so it would silently drop the BGE prefix; prefix kept explicit.
- Learner predictions (2026-10-12, before the run): (1) "second call is slower" because
  the first embeds all chunks into the vector DB and the second only embeds the question
  (the answer says both "slower" and "faster"; "not completely sure"). (2) "I don't know".
  Gap: (1) answers a different question: `get_model()` only loads the model; no chunks and
  no vector DB are involved in this step yet.
- Real output: n/a (pending).

### 2026-10-10, session 7c: Phase 1 step 1a.3 (chunker.py)

- `src/docpilot/chunker.py` + `tests/test_chunker.py` (5 tests + 1 test run with 4 bad
  settings). ruff passes; full suite (loader + chunker) passes on made-up data.
- Changed from the plan: defaults read from `config` (no second copy of 800/100); added a
  "no text is lost" rebuild test; `pairwise` instead of `zip(chunks, chunks[1:])` (B905).
- Learner predictions (2026-10-12, written before the run; 36-character text at 10/3):
  (1) "5 chunks"; (2) last chunk "23456789", 8 characters, "due to the overlapping";
  (3) last chunk at 800/100 is not always 800: it is whatever is left; if a dev needs 800,
  "add dummy ones like zeros and ones" to pad it.
- Real output: 5 chunks; lengths 10/10/10/10/8; last `'23456789'`. pytest: 9 passed.
  (1) correct. (2) correct; the "why" is half right: overlap sets where the last chunk
  starts (28), the text running out sets its length (36 - 28 = 8). (3) first half right
  (not always 800); padding idea **wrong**: dummy text changes the embedding and costs LLM
  tokens; the tokenizer pads internally with an attention mask. The real issue is tiny
  tail chunks (101 to 800 chars at 800/100) - a Phase 2 idea.
- Homework: predict, then run, the last chunk at `chunk_size=10, overlap=0`.
- `USER_GUIDE.md` reached 489 lines: continued in `docs/2_USER_GUIDE.md` (Rule 12).

### 2026-10-09, session 7b: Phase 1 step 1a.2 (loader.py)

- 1a.1 committed by the learner (`f016014`).
- `src/docpilot/loader.py` (34 lines) + `tests/test_loader.py` (4 tests on fake folders).
  ruff passes; 4 tests pass on made-up data.
- Plan bugs fixed openly: missing folder returned `[]` silently (now `FileNotFoundError`);
  a folder named `*.md` crashed `read_text` (now `is_file()`); `sorted(Path)` order differs
  Windows vs Linux (now sort by `source` string).
- Learner predictions (2026-10-10, written before the run):
  (1) "if there is no file in the folder it returns an error and if not folder also";
  (2) missing folder: "if not folder.is_dir() ... raises FileNotFoundError ... line 19".
- Real output: (1) real `data/docs` (only `.gitkeep`) -> `[]`, no error. Prediction 1
  **wrong**: an existing but empty folder is not an error; only a missing folder is.
  (2) `no_such_folder` -> `FileNotFoundError: Docs folder not found: no_such_folder`,
  raised at loader.py line 19. Prediction 2 **correct**. pytest: 4 passed in 0.16s.
- Open question for 1a.8: should `02_ingest.py` stop when `load_documents` returns `[]`?
  (Yes: the loader returns facts, the script decides what is fatal.)

### 2026-10-09, session 7: Phase 1 step 1a.1 (config.py)

- Learner chose to start Phase 1 before closing the Phase 0 gate (Lab 2 sentences, Phase 0
  interview notes, tag `phase-0`); those stay open. This breaks the phase-gate rule once,
  on purpose, and is recorded here.
- python-dotenv 1.2.4 checked on PyPI (2026-10-09), pinned in `requirements.txt`, added to
  the lock file, decision D-026.
- Plan bug fixed openly: the plan's `config.py` had no `EMBEDDING_REVISION`, so Phase 1
  would have loaded unpinned model files while the labs used pinned ones. Added it.
- `src/docpilot/config.py` built (47 lines); ruff check + format pass; import works.
- Learner prediction for `print(config.DOCS_DIR)`: none written (gap, again). Bonus
  prediction (`LLM_MODEL` without `.env`): none written.
- Real output: `C:\Users\rajes\OneDrive\Desktop\1\AIML\9_DOCPILOT_RAG_BASED\docpilot_rag\data\docs`.
  Done-when check passes. Learner first read this as "no output": the one printed line IS
  the output (a `print` of a path shows only the path, with no label).

### 2026-10-08, session 6: scope change v1.1 (new technologies)
- Learner added: AWS (EC2, S3, ECR, IAM, CloudWatch, VPC) as main target on the free plan
  with Oracle as fallback; Terraform; MinIO + boto3; k3s planned; EKS exercise; MLflow from
  Phase 2; RAG monitoring; stronger Git workflow; and asked for child-level teaching of evals
  and guardrails.
- Verified on the web (2026-10-08): AWS free plan terms; EKS USD 0.10/h, no free tier; public
  IPv4 USD 0.005/h; MinIO community edition archived (Apr 2026) and images/binaries removed
  (Sep 2026); MLflow 3 has GenAI tracing; Terraform BSL / OpenTofu MPL; k3s 2 GB RAM minimum.
- Learner decisions: SeaweedFS replaces MinIO; AWS account created at start of Phase 7;
  long-term home = Oracle (move before month 6).
- Wrote 10 new primers (`teaching/primer_*.md`), `architecture/3_architecture.md`,
  `implementation_plan/3_` and `4_phase_7_production.md`, `interview/2_phase_7_interview.md`;
  updated plans (1f, 2.0, 2.10, 3.1b, Phase 7 renumbered 7.1-7.19), architecture, teaching,
  interview files, decisions D-017 to D-025, RULEBOOK (Rules 2, 12, 14, new 17),
  PROJECT_DOCUMENTATION v1.1, USER_GUIDE, CHAT_CONTEXT, CLAUDE.md.
- Estimated total time now 10-12 weeks.

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

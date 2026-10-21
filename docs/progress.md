# DocPilot Progress

Update this file at the end of every session. Newest session log entry goes on top.

---

## Right now

| Item | Value |
|---|---|
| Current phase | Phase 3 (Phase 2 gate closed 2026-10-20: PR #3, tag `phase-2`) |
| Current step | 3.1b done: SeaweedFS + boto3 + MLflow server (D-051) |
| Next step | learner: commit 3.1b; then 3.2 sparse (BM25) vectors: raw BM25 lab first |
| Blockers | none (the old "code missing" blocker is closed: steps 1a.1 to 1a.8 are in this repo) |
| Homework | Rewrite the mentor-drafted Phase 0/1/2 answers in `interview_notes.md` in your own words; practise them aloud |

---

## Phase checklist

Status values: `not started`, `in progress`, `done`, `blocked`.

### Phase 0: Foundations
| Step | What | Status |
|---|---|---|
| 0.1 | Project skeleton (folders, `.gitignore`, `.env.example`) | done (commit 497a9a4) |
| 0.2 | Virtual environment, `pyproject.toml`, pinned `requirements.txt` | done (commit 497a9a4) |
| 0.3 | `labs/lab1_embeddings.py` (embeddings and cosine similarity) | done (commit 5924b95) |
| 0.4 | Lab 2: keyword vs meaning search | done (two sentences mentor-drafted at learner's request, 2026-10-15) |
| Gate | tag `phase-0` | done 2026-10-15 (tag on `0a1e689`; notes mentor-drafted) |

### Phase 1: Naive baseline, eval harness, mini API
| Step | What | Status |
|---|---|---|
| 1a.1 | `config.py` (+ python-dotenv 1.2.4, D-026) | done (run 2026-10-09; not yet committed) |
| 1a.2 | `loader.py` + `tests/test_loader.py` | done (run 2026-10-10; 4 tests pass) |
| 1a.3 | `chunker.py` + `tests/test_chunker.py` | done (run 2026-10-12; 9 tests pass) |
| 1a.4 | `embedder.py` + `tests/test_embedder.py` | done (commit 8eff576; learner run skipped) |
| 1a.5 | `vector_store.py` + `tests/test_vector_store.py` (qdrant-client 1.19.1, D-027) | done (run 2026-10-12; 5 tests pass) |
| 1a.6 | `llm.py` + `tests/test_llm.py` (openai 3.29.0, gpt-oss-120b, D-028) | done (run 2026-10-12; first real Groq call) |
| 1a.7 | `rag.py` + `tests/test_rag.py` | done (demo run 2026-10-12) |
| 1a.8 | scripts `01_download_docs.py`, `02_ingest.py`, `03_ask.py` (D-029) | done (run 2026-10-12 by the mentor: 51 chunks, ingest 7.5 s) |
| 1b | Ask 10 questions, write `docs/failure_log_phase1.md` | done (run 2026-10-12; 10 rows + mentor's draft summary) |
| 1c | Golden dataset v0 (about 30 questions, dev/test) | done (2026-10-12: 32 items, validator OK; learner review pending) |
| 1d | Retrieval eval harness, record C0; latency baseline L0 (D-031) | done 2026-10-14 (learner runs): C0 retrieval, L0, abstention; test split at the gate |
| 1e | Mini FastAPI `POST /ask` | built + tested 2026-10-14 (4 API tests; server boots, /docs 200); learner's live /ask pending |
| 1f | Git workflow: public repo, PR template, CI `test`, branch protection | files built 2026-10-14 (ci.yml, PR template, length check); done 2026-10-15: draft PR #1, CI green (run 38682492687); branch protection deferred to project end (D-035) |
| Gate | tag `phase-1` | done 2026-10-15 (PR #1 merged; notes mentor-drafted; protection deferred, D-035) |

### Phase 2: Ingestion quality and chunking
| Step | What | Status |
|---|---|---|
| 2.0 | MLflow tracking; re-log C0 | built 2026-10-15 (D-036; 4 tests; smoke re-log equal to JSON); learner saw C0 runs in the UI and compared dev vs test (2026-10-15) |
| 2.1 | Refactor into `ingestion/` package | done 2026-10-15: 66 tests pass; regression check C0-2.1 == C0 on all metrics and all 19 questions (`785120a`) |
| 2.2 | Cleaner (HTML noise) | built 2026-10-15 (7 tests; 144 tags -> 0; 30 code blocks byte-identical); C0+clean dev R@5 0.947, MRR 0.665 (2026-10-17) |
| 2.3 | Include resolver (`{* ... *}` markers) | built 2026-10-17: 18 code files downloaded, includes resolved 29, missing 0; C0+clean+incl dev R@5 0.895, MRR 0.643 (2026-10-17) |
| 2.4 | Block parser (code, tables, headings kept whole) | built 2026-10-17 (7 tests; real pages: 0 lines lost, 63 code blocks whole, lists kept whole) |
| 2.5 | Metadata (source, heading path, doc type, version, technology) | built 2026-10-17 (payload only; text unchanged) |
| 2.6 | Six chunking strategies | done 2026-10-19: rows C1-C4 + controls (v0, dev); C5 skipped by learner; leader C4-200 (D-042) |
| 2.7 | Docling for PDF, Word (DOCX), HTML (D-037) | built 2026-10-19 (D-043); PDF swapped to Chain-of-Thought 2026-10-20 (D-044, 43 pages/8 tables); notes DOCX; golden v0.2; HTML not needed |
| 2.8 | More corpora + golden set v1 | done 2026-10-20 (D-045): Pydantic, Docker, Wikipedia x3, interview notes; golden v1 = 65 items; C0-v1 dev R@5 0.780 |
| 2.9 | Index per strategy, run evals, per-type breakdown | done 2026-10-20: fixes A/B/C, 11-config matrix (D-046), winner FT-200 (D-047): dev R@5 0.805 / MRR 0.701; test R@5 0.882 vs C0 0.941 (ranking gain only) |
| 2.10 | CI retrieval eval gate (fixture corpus) required on `main` | done 2026-10-20 (D-048): baseline R@5 1.000 / MRR 0.870; red-PR demo #2 (units bug) failed as expected; "required" impossible while private (D-035) |
| Gate | C1 to C5 rows filled, strategy chosen; tag `phase-2` | done 2026-10-20: PR #3 merged to main (test, eval-gate green), tag `phase-2` pushed; C5 skipped (D-049); interview answers = mentor drafts (homework: rewrite) |

### Phase 3: Retrieval upgrade
| Step | What | Status |
|---|---|---|
| 3.1 | Docker primer; Qdrant in Docker | done 2026-10-21 (D-050): qdrant v1.19.1 (amd64+arm64), scores identical to local; search p50 7.6 ms via 127.0.0.1 (localhost = 2 s IPv6 trap) |
| 3.1b | SeaweedFS + boto3 object storage; MLflow server | done 2026-10-21 (D-051): docs round-trip byte-identical, index from S3 copy + snapshot restore give identical scores, 32 runs + artifacts on the MLflow server; named volumes (OneDrive folder: 621 MB / 91 s snapshot -> 2 MB / 0.3 s) |
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

Sessions from 2026-10-14 on continue in [2_progress.md](2_progress.md) (500-line rule).

### 2026-10-13, session 9: Phase 1 step 1d (eval harness), built

- Learner had asked "teach me evals" (session 8c, chat only; primer_evals.md already covers
  it). 1c not yet committed when 1d started.
- Files: `evals/__init__.py`, `matching.py`, `metrics.py` (+ `mean`, nearest-rank
  `percentile`), `common.py` (load split after validation, git commit with `+dirty`, save
  result, 429-counting `ask_with_retries`), `run_retrieval_eval.py`, `run_latency.py`,
  `run_abstention_check.py`, `ABLATION.md` (all n/a); tests `test_metrics.py` (11,
  hand-computed) and `test_matching.py` (8). Decision D-033.
- Plan fixes: run as `python -m evals.<script>` (import path); `numpy`-free percentile.
- Smoke runs (exit code and JSON structure only, scores NOT read, files deleted):
  retrieval exit 0 (19 answerable dev items, 7 types); latency and abstention with
  `--limit 1`, exit 0 (4 LLM calls). Full suite 58 passed; ruff clean.
- Learner predictions: n/a (pending). Real C0 / L0 / abstention: n/a (pending).

### 2026-10-12, session 8b: Phase 1 step 1c (golden dataset v0)

- Learner asked to implement 1c. Mentor drafted all items (learner short on time), each
  snippet copied from the 4 downloaded pages.
- Files: `evals/golden/dev.jsonl` (22), `test.jsonl` (10), `README.md`;
  `evals/validate_golden.py`; `tests/test_validate_golden.py` (7 tests: typo, duplicate id,
  missing field, unanswerable with evidence, wrong split file, broken JSON);
  `pyproject.toml` pytest `pythonpath = ["."]`; decision D-032.
- Real output: `validate_golden.py` -> 32 items; dev 22 (3 unanswerable), test 10 (2
  unanswerable); OK. Full suite: 39 passed. Ruff clean on src, scripts, tests, evals, labs.
- Plan fix: "cover every type in section 2" is not possible on 4 pages since v1.2 added
  concept/interview/adversarial/risky; deferred types listed in the README and D-032.
- Test split has not been run against DocPilot (and must not be until a gate).

### 2026-10-12, session 8: Phase 1 step 1b (failure log), set up

- Picked up from session 7i by handoff. Git: learner committed 1a.8 (`d5eb042`) and the
  v1.2 docs (`bb4709f`). `data/docs/fastapi/` already holds the 4 pages and a
  `qdrant_local/` folder exists; the learner still re-runs 01 and 02 so the index is
  fresh from the committed code.
- Learner asked to implement step 1b. Done: `docs/failure_log_phase1.md` (10 questions,
  one or more per type: how-to, not-in-docs, factual x2, exact identifier, paraphrase,
  comparison, code, table/list, multi-hop; an answer key with page + section, written
  from reading the pages; a "Prediction" column added to the plan's table so every row is
  predicted before it is run; the three summary lines).
- `03_ask.py --full`: prints whole chunks. Why: the 200-char preview cannot show whether
  the right passage is in a chunk. Ruff passes. No new dependency.
- Q3 (status code) is deliberately a trap: judge the answer only against the 4 pages.
- Learner predictions (2026-10-12, before any run, no reasons given): Q1 "perfect answer
  from the docs"; Q2 "it will say it is not in the document"; Q3 "takes the retrieved
  text, adds some LLM content, and answers". Q4 to Q10 and the 1a.8 chunk/latency
  predictions: n/a (not given). Real output: n/a (pending).
- Learner asked: how can I know what is in the docs without reading them all (answer:
  search with Select-String, read only the section), and "is this what evals are?"
  (answer: 1b is manual error analysis; 1c + 1d turn it into evals).
- Learner then said "no time, you run it all and note it". Mentor ran 01, 02 and the 10
  questions (`--full`) on 2026-10-12, laptop CPU, Groq `openai/gpt-oss-120b`.
- 1a.8 real: 4 pages downloaded (commit d623544); chunks body 10, first-steps 21,
  path-params 13, query-params 7 = **51**; ingest 7.5 s (2 batches).
- 1b real: right chunk in top 4 (at least partly) for 8/8 answerable questions; answers:
  6 fully right, 2 partly (Q1 ungrounded code "from the docs", Q10 multi-hop missing the
  how), 1 wrong (Q7 `NOT_FOUND` because only include markers were indexed); both
  abstention questions (Q2 PostgreSQL, Q3 status code: "422" is in none of the 4 pages)
  gave `NOT_FOUND`. Q2 irrelevant top score 0.705 > Q5 correct chunk 0.700.
- Timings, 10 single cold runs (one process each, so each includes the model load):
  embed_query 2017 to 2204 ms, search 1.3 to 1.9 ms, llm 896 to 1553 ms, total 2983 to
  3717 ms. These are not p50/p95 and not warm; L0 comes in 1d.
- Bug found and fixed: `03_ask.py` `UnicodeEncodeError` (cp1252) when output is redirected
  on Windows; `sys.stdout.reconfigure(encoding="utf-8")`. Citation format: `【n】` in 3/10
  answers.

### 2026-10-12, session 7i: scope v1.2 (wider corpus) + latency

- Learner answers: corpus groups A docs + B learning material + C interview prep accepted;
  own notes yes, other sources welcome (non-open = `local_only`); no general "any document"
  chatbot, uploads only as stretch after guardrails; Phase 1 unchanged, widening in 2.8.
- Learner asked to make latency explicit (before and after deployment). It existed in
  Phases 3/4/6/7 but had no primer, no Phase 1 baseline, no measuring rules, no TTFT.
- Done: PROJECT_DOCUMENTATION v1.2 (changelog, scope table, users, question types,
  non-goals, performance row, decision rows); decisions D-030 (corpus), D-031 (latency);
  CLAUDE.md; Phase 1 part 2 (`evals/run_latency.py`, L0 in the gate); Phase 2 (domain
  metadata, Q&A-pair chunker, corpus register, per-domain table); Phase 3.8 (domain
  filter); Phase 8.6 (uploads); architecture part 1; `teaching/primer_latency.md` (new);
  phase 1 interview Q15; `2_USER_GUIDE.md` section 22.
- Code: `ask()` returns `timings_ms` (embed_query, search, llm, total); `03_ask.py` prints
  them (1 cold run); new test `test_ask_times_every_stage`. Full suite: 32 passed.

### 2026-10-12, session 7h: Phase 1 step 1a.8 (scripts)

- 1a.7 committed by the learner (`db73bd8`). Learner later added a blank line inside
  `SYSTEM_PROMPT` in `rag.py` (uncommitted); harmless, but it is now part of the C0 prompt.
- Corpus chosen and checked (D-029): 4 FastAPI tutorial pages at commit `d62354434b2e`,
  URLs 200, licence MIT.
- `scripts/01_download_docs.py`, `02_ingest.py`, `03_ask.py`; ruff passes; `03_ask.py
  --help` works; full suite 31 passed. Downloads and ingest NOT run (learner's run).
- Learner asked (2026-10-12): document step 1a.8 (done: `2_USER_GUIDE.md` section 21) and
  start `docs/interview/challenges_and_failures.md` with **big failures only** (done: 4
  entries). Scope widening (interview prep, ML/LangChain/LangGraph learning material) is
  being discussed first; no scope docs changed yet.
- Learner predictions: n/a (pending). Real output: n/a (pending).

### 2026-10-12, session 7g: Phase 1 step 1a.7 (rag.py)

- 1a.6 committed by the learner (`a935dac`).
- `src/docpilot/rag.py` + `tests/test_rag.py` (4 tests, fakes for search and LLM).
  Full suite: 31 passed in 19.51 s.
- Changed from the plan: empty index -> NOT_FOUND without an LLM call; type hints.
- Learner predictions (before the run): (1) Q1: doc0 is the source and the answer; (2) Q2:
  will NOT say the NOT_FOUND phrase, the LLM will add technical information itself;
  (3) Q2 sources: "source 3 is related to Q2, not sure".
- Real output (3 handmade chunks, gpt-oss-120b): Q1 answer `q: str | None = None` with one
  `[1]` at the end; sources doc0 0.882, doc1 0.590, doc2 0.446. Q2 answer exactly
  `I could not find this in the documents.`; sources doc2 0.604, doc1 0.442, doc0 0.421.
  (The learner's paste shows Q2's answer and first source twice; the code prints each once,
  so most likely a terminal/copy artefact.) pytest: 4 passed in 11.41 s.
- Verdict: (1) correct. (2) **wrong**: the model abstained as told (1 example only).
  (3) **wrong**: 3 sources, all chunks (top-k always returns k, or all if fewer). Q2's top
  score 0.604 for an unrelated chunk is higher than Q1's #2 (0.590): a raw score is not a
  "relevant" signal. The LLM, not retrieval, did the abstaining here.
- HF Hub "unauthenticated requests" warning: harmless; the model is cached (D-002 pin).

### 2026-10-12, session 7f: Phase 1 step 1a.6 (llm.py)

- 1a.5 committed by the learner (`e298493`).
- `.env` checked without reading values: GROQ, OPENROUTER, GEMINI keys set; `LLM_MODEL`
  empty.
- openai 3.29.0 checked on PyPI, installed, pinned, lock regenerated; Groq docs (models,
  rate limits, reasoning) and the account's `/models` list checked; decision D-028
  (model `openai/gpt-oss-120b`). Free-plan rate limits: n/a (docs show the Developer table).
- Plan bugs fixed: empty answer silently returned as `""`; defaults frozen at import;
  `KeyError` for unknown provider.
- `src/docpilot/llm.py` + `tests/test_llm.py` (5 tests, fake client). Full suite: 27
  passed (13.3 s warm; 56.9 s on the first cold run after installing openai).
- Learner concern (2026-10-12): "I am not having OpenAI, I want the free one". Clarified:
  `openai` is a free open-source client library (no account); `openai/gpt-oss-120b` is an
  open-weight model hosted free on Groq; nothing is paid, no OpenAI account is used.
- Learner predictions (before the run): (a) temperature 0 does not guarantee identical
  answers, "there might be some changes"; (b) `llama-3.3-70b-versatile` "is deprecated";
  Groq will not pick another model by itself; raises an error, "404 I think, not sure".
- Real output (`LLM_MODEL=openai/gpt-oss-120b`): two calls both returned
  `'FastAPI is a modern, high‑performance Python web framework for building APIs with
  automatic documentation.'`; identical: True; 2.1 s for 2 calls. `llama-3.3-70b-versatile`
  -> `openai.NotFoundError: Error code: 404 ... model_not_found` ("does not exist or you do
  not have access to it"). Learner's extra call with `gpt-oss-120b` and "hi": "Hello! How
  can I help you today?". pytest: 5 passed in 0.93 s.
- Verdict: (a) learner called it a mistake, but the reasoning was sound: temperature 0 is
  not a guarantee; 1 identical pair out of 1 is too small to prove it (D-007 spirit: no
  over-claiming). (b) correct (error, 404, no silent switch); "deprecated" is not shown:
  the message says "does not exist or you do not have access".
- Noticed: the answer has a non-breaking hyphen (U+2011) in "high‑performance". Evals that
  compare text (e.g. NOT_FOUND_PHRASE) must normalise text first (step 1d/3.9 note).

### 2026-10-12, session 7e: Phase 1 step 1a.5 (vector_store.py)

- qdrant-client 1.19.1 checked on PyPI, installed, pinned, lock regenerated (60 packages;
  new: pydantic 2.14.1, grpcio, protobuf, portalocker, pywin32 ...), decision D-027.
- API verified on the installed version with fake vectors: `query_points` works,
  `search()` removed, second client on the same folder raises `RuntimeError` (D-003).
- **Bug found by `test_fresh_collection_is_empty`** (failed: `assert 3 == 0`): local mode
  on disk brings old points back after delete + create. Workaround: delete all points with
  an empty filter + check. Without the test, Phase 2 re-ingests would mix old and new chunks.
- `src/docpilot/vector_store.py` (76 lines) + `tests/test_vector_store.py` (5 tests).
  Full suite: 22 passed in 18.10 s.
- Learner predictions (2026-10-12, before the run): (1) chunk 1 first, chunk 2 second,
  "cuz the 0.99 is near to one"; (2) count stays 3 "cuz we delete the collection if it
  exists and re-create it".
- Real output: `count 3`; `text 1 0.994`, `text 2 0.11`, `text 0 0.0`. pytest: 5 passed
  in 1.58 s. (1) order **correct**; score above 0.9 correct (0.994), because cosine
  ignores length: 0.9 / sqrt(0.9^2 + 0.1^2) = 0.994. (2) count **correct**, reason
  **wrong**: `create_fresh_collection` ran once, before both adds; the count stays 3
  because `upsert` with the same uuid5 ids overwrites (random uuid4 ids would give 6).

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
- Real output: **skipped by the learner** (2026-10-12: "let's skip it"). Open questions
  (lru_cache speed; query vs document vector for the same word) stay unanswered.

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

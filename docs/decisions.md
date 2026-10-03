# DocPilot Decision Log

Every entry answers: **what, why, alternatives, trade-offs, date, evidence**.
"Verified on" is the date we checked the current official docs or free-tier limits (Rule 4).
Evidence is filled only with real eval numbers, or `n/a`.

D-001 to D-011 are copied from `PROJECT_DOCUMENTATION.md` section 19.

---

## Summary table

| ID | Decision | Status | Date | Verified on | Evidence |
|---|---|---|---|---|---|
| D-001 | Domain: technical documentation | accepted | 2026-10-03 | n/a | n/a |
| D-002 | Embeddings: `bge-small-en-v1.5` | accepted (revisit Phase 3) | 2026-10-03 | not yet | n/a |
| D-003 | Vector DB: Qdrant, local mode then Docker | accepted | 2026-10-03 | not yet | n/a |
| D-004 | OpenAI-compatible LLM client; Groq default, Ollama fallback | accepted | 2026-10-03 | not yet | n/a |
| D-005 | Settings in `config.py`, secrets in `.env` | accepted | 2026-10-03 | n/a | n/a |
| D-006 | Fixed-size chunking as weak baseline | accepted | 2026-10-03 | n/a | n/a |
| D-007 | Evals before features | accepted | 2026-10-03 | n/a | n/a |
| D-008 | System prompt as first weak guardrail | accepted (replace Phase 6) | 2026-10-03 | n/a | n/a |
| D-009 | Tracing tool | **open** (decide Phase 7) | n/a | not yet | n/a |
| D-010 | Gold labels by doc + verbatim snippet | accepted | 2026-10-03 | n/a | n/a |
| D-011 | CI gate on retrieval-only evals | accepted | 2026-10-03 | n/a | n/a |
| D-012 | Docs structure and 500-line rule | accepted | 2026-10-03 | n/a | n/a |
| D-013 | `src/` layout with editable install | accepted | 2026-10-03 | n/a | n/a |
| D-014 | Generation eval harness placed at end of Phase 3 | proposed | 2026-10-03 | n/a | n/a |
| D-015 | Python 3.12+ (dev on 3.13.2) instead of 3.11+ | accepted | 2026-10-03 | 2026-10-03 (PyPI) | numpy 2.5.3 requires >=3.12 |
| D-016 | Split requirements (runtime / dev) + generated lock file | accepted | 2026-10-03 | n/a | n/a |

---

## Full entries

### D-001 Domain: technical documentation
- **What:** index official docs of FastAPI, Docker, LangGraph, Qdrant, Pydantic, Redis.
- **Why:** the builder uses these docs daily; they contain code, tables, and exact
  identifiers that break naive RAG, so improvements are measurable.
- **Alternatives:** legal/regulation corpus, finance filings.
- **Trade-off:** licensing. Downloaded docs are never committed; a script recreates them.

### D-002 Embeddings: `BAAI/bge-small-en-v1.5`
- **Why:** free, local, 384 dimensions, fast on CPU, strong for its size.
- **Alternatives:** `bge-base`, `bge-m3`, `nomic-embed-text`, `e5`; paid OpenAI/Cohere.
- **Why not paid:** costs money and sends data off the machine.
- **Revisit:** Phase 3 embedding comparison with eval numbers.

### D-003 Vector DB: Qdrant
- **Why:** open source, dense + sparse vectors in one place, payload filters, runs in Docker.
- **Alternatives:** Chroma (simpler, fewer production features), pgvector (great if already
  on Postgres), FAISS (a library, not a database), Pinecone (managed, paid).
- **Trade-off:** local mode allows only one process at a time; move to Docker in Phase 3.

### D-004 LLM access
- **Why:** one OpenAI-compatible client works for Groq, OpenRouter, and Ollama, so switching
  provider is a config change.
- **Alternatives:** one SDK per vendor.
- **Revisit:** LiteLLM gateway in Phase 7.

### D-005 Settings and secrets
- **Why:** experiments change one value in one place; keys never land in git.

### D-006 Fixed-size chunking as baseline
- **Why:** gives an honest, weak number to beat. Starting with the best strategy hides how
  much each improvement is worth.

### D-007 Evals before features
- **Why:** without a baseline number, "it got better" is an opinion.

### D-008 System prompt as first guardrail
- **Why:** zero cost, teaches the idea. Known weak; Phase 6 measures how often it fails.

### D-009 Tracing tool (open)
- **Options:** Langfuse self-hosted (several services, heavy for a small VM), Langfuse Cloud
  free tier, Arize Phoenix (lighter, self-hostable).
- **Decide:** Phase 7, after checking current docs and limits.

### D-010 Gold labels by document + snippet
- **Why:** chunk ids change with every chunking strategy; a snippet does not.
- **Trade-off:** a snippet can be split across two chunks; use an overlap threshold.

### D-011 CI gate on retrieval-only evals
- **Why:** deterministic and costs no LLM tokens. Generation evals run nightly or manually.

### D-012 Docs structure and the 500-line rule
- **What:** docs split into `architecture/`, `implementation_plan/`, `teaching/`,
  `interview/`, plus `progress.md`, `decisions.md`, `RULEBOOK.md`. Max 500 lines per file;
  Markdown continues in `2_<name>.md`; Python splits by responsibility (a module name cannot
  start with a digit).
- **Why:** learner request; small files are easier to read, review, and explain.
- **Exception:** `PROJECT_DOCUMENTATION.md` stays as written unless the learner asks.

### D-013 `src/` layout with editable install
- **What:** code in `src/docpilot/`, installed with `pip install -e .`.
- **Why:** imports work the same from scripts, tests, and the API; tests run against the
  installed package, which catches packaging mistakes early.
- **Alternative:** flat folder with `sys.path` hacks. Why not: fragile and breaks in Docker.

### D-014 Generation eval harness at end of Phase 3 (proposed)
- **What:** `PROJECT_DOCUMENTATION.md` lists faithfulness and relevancy columns for every
  config, but Phase 1 only requires retrieval metrics for C0. We build a small plain-Python
  judge in step 3.9, before Phase 4 needs it, and back-fill C0 and the best configs.
  Abstention accuracy (deterministic phrase check) starts in Phase 1.
- **Why:** Phase 4 must compare agentic vs non-agentic on answer quality, which needs
  generation metrics. Judge calls cost free-tier tokens, so we do not run them on every
  chunking config.
- **Status:** proposed; learner to confirm.

### D-015 Python 3.12+ (develop on 3.13.2)
- **What:** `requires-python = ">=3.12"`; local venv uses Python 3.13.2.
- **Why:** the current numpy (2.5.3, checked on PyPI 2026-10-03) requires Python 3.12+, so
  the "3.11+" in `PROJECT_DOCUMENTATION.md` section 8 no longer holds with today's packages.
  3.13 was already installed on the learner's machine.
- **Alternatives:** install 3.11 and pin an older numpy. Why not: older packages for no gain.
- **Trade-off / follow-up:** the Phase 7 Dockerfile must use the **same** minor version
  (`python:3.13-slim`) so dev, CI, and production match. Check arm64 wheels for 3.13 for
  every heavy dependency (torch, spaCy/Presidio) when Docker arrives in Phase 3.

### D-016 Split requirements + lock file
- **What:** `requirements.txt` (runtime, pinned direct dependencies), `requirements-dev.txt`
  (`-r requirements.txt` + pytest, ruff), `requirements-lock.txt` (generated by
  `pip freeze`: every package including indirect ones such as torch and transformers).
- **Why:** test and lint tools do not belong in the production image. Pinning only direct
  dependencies still lets indirect ones (torch!) change under us; the lock file records the
  exact full set that was tested.
- **Alternatives:** dependencies in `pyproject.toml` (fine, but pins there are awkward for
  an app); pip-tools / uv / poetry lock files (good tools; one more thing to learn now).
- **Trade-off:** the lock file is generated on Windows; Linux/ARM may resolve slightly
  differently (e.g. torch CPU vs CUDA builds). Revisit in Phase 7 when building images.

---

## Version pins (filled when verified)

| Package | Version | Verified on | Notes |
|---|---|---|---|
| python | 3.13.2 (requires >=3.12) | 2026-10-03 | D-015 |
| sentence-transformers | 6.1.0 | 2026-10-03 | latest on PyPI; pulls torch + transformers |
| numpy | 2.5.3 | 2026-10-03 | requires Python >=3.12 |
| torch (indirect) | 2.14.1+cpu | 2026-10-03 | Windows PyPI wheel is CPU-only; cuda available = False |
| transformers (indirect) | 5.18.0 | 2026-10-03 | via sentence-transformers |
| setuptools (build) | >=68 (84.0.0 installed) | 2026-10-03 | build backend only |
| qdrant-client | n/a | n/a | |
| openai | n/a | n/a | |
| python-dotenv | n/a | n/a | |
| fastapi | n/a | n/a | |
| uvicorn | n/a | n/a | |
| pytest | 9.1.1 | 2026-10-03 | dev only |
| ruff | 0.16.10 | 2026-10-03 | dev only |

## Free-tier checks (filled when verified)

| Service | What was checked | Result | Verified on |
|---|---|---|---|
| Groq | models, rate limits | n/a | n/a |
| Gemini | free limits, data-use terms | n/a | n/a |
| OpenRouter | current free models | n/a | n/a |
| Oracle Cloud | Always Free allowance, region | n/a | n/a |

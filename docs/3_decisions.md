# Decision Log (part 3)

Continues [2_decisions.md](2_decisions.md) (D-038 to D-056), which reached the
500-line limit. Same format: what, why, alternative, why not.

---

## D-057: generation eval v0 with an LLM judge; step 3.7 built but not run (2026-10-22)

- **What:** `evals/run_generation_eval.py` + `evals/judge_prompts.py`: retrieve (best or
  dense) -> `rag.generate()` -> ONE judge call (claims + supported, correctness yes/partly/no,
  relevancy 1-5) -> deterministic abstention check. Generator and judge outputs cached;
  ~20% of judged items written to `evals/spot_checks/` for a human verdict. MLflow
  experiment `docpilot-generation`. `git_commit()` ignores `evals/spot_checks/`.
- **Judge:** `qwen/qwen3.8-27b` on Groq (listed on `/openai/v1/models` with the learner's
  key, 2026-10-22; preview model, may disappear). Different family from the generator
  (gpt-oss), so it does not grade its own style (Rule 11). Temperature 0. Smoke test: it
  caught a planted unsupported claim (faithfulness 0.5).
- **Numbers (`4c75fac`, 10 judged + 5 unanswerable):** faithfulness 1.000, hallucination
  rate 0.000, correctness 1.000, relevancy 5.0, abstention 1.000, LLM p50 990 ms.
- **Why one judge call and n=10:** free-tier tokens (200K per day per model); one call does
  all three checks; the cache makes a later `--n 20` pay only for the new questions.
  **G-dense not run** (deadline, quota).
- **Step 3.7 (embedding comparison):** `evals/compare_embedders.py` is built and tested
  (5 models pinned, prefixes from the model cards) but **not run**: the 3-day deadline and
  a 3.5 GB download for a model change we would also have to re-index for. bge-small stays
  (D-002). `psutil==7.2.2` (already in the lock via accelerate) pinned in
  requirements-dev for its RAM column.
- **Alternative:** RAGAS / DeepEval. **Why not now:** own metrics first (Rule 8); they also
  need an LLM per metric (more quota).

## D-058: one retrieval front door in the app; scope cut for the deadline (2026-10-22)

- **What (step 3.10):** `retrieval/pipeline.py`: `RetrievalSettings` (hybrid, rerank
  candidates, reranker, top_k, ...), `BEST` (hybrid + MiniLM rerank 20, top 4) and
  `DENSE_ONLY` (the Phase 1/2 app), `retrieve()` (times embed/search/rerank) and
  `warm_up_models()`. `rag.ask()` now uses `retrieve()` (default BEST) and `generate()`;
  the API loads all models at startup (no cold first request). One real question: 4/4
  chunks from the right Docker page; embed 75, search 40, rerank 993, LLM 1591 ms (n=1).
- **Scope cut (learner, 2026-10-22, 3 days to submission):** Phase 4 (agents) and Phase 5
  (multi-agent, HITL) dropped; Phase 8 stretch dropped; 3.7 and 3.8 (metadata filters: 453
  chunks, 12 ms search, misses are tables not wrong-technology) skipped. Kept: light
  guardrails (Phase 6) and the core of Phase 7 production: Docker image, Prometheus +
  Grafana latency monitoring, GitHub CI/CD to GHCR, AWS S3 via Terraform (EC2 if time).
  `PROJECT_DOCUMENTATION.md` still describes the full plan; the README marks the dropped
  parts as future work. Never present them as done.

## D-059: Phase 6 light guardrails in plain Python, measured by a red-team run (2026-10-22)

- **What:** `src/docpilot/guardrails/`: `input_guard.py` (empty, too long, NFKC +
  zero-width clean-up, 4 injection pattern groups), `context_guard.py` (chunks in
  `<document id source>` boxes, `</document>` inside text escaped), `output_guard.py`
  (canary leak -> blocked, exact not-found sentence, cite-or-refuse incl. `【n】` and
  `【n†Lx-Ly】` styles, citation range check, API-key redaction). `rag.ask(guarded=True)`
  is the default; `guarded=False` keeps the Phase 3 pipeline for the "before" row. API
  returns `status` + `timings_ms`, never the rule that fired (logged server-side).
  `config.BLOCKED_PHRASE`. Red team: `evals/redteam/attacks.jsonl` (18 attacks, 6
  categories, deterministic markers), `evals/run_redteam.py` (cached LLM replies, poisoned
  chunk forced to rank 1). Generation eval `--guarded` (own cache file). +51 tests (252).
- **Numbers (`81e119d+dirty`; RT-v1 re-run clean on `9d3b85d` 2026-10-23, identical counts):** attack success 2/18 (0.111) before ->
  0/18 after; after-run stops: input guard 8, prompt/model 10, output guard 0. False
  blocks: input guard 0/84 golden questions, output guard 0/10 cached good answers. Guard
  time p50 0.012 ms (input), 0.042 ms (output). G-guard (dev, 10 + 5): faithfulness 1.0,
  correctness 1.0 (9 judged), **1 false refusal** (q-003, the model refused under the
  stricter prompt; old prompt answered "422 [3]"), abstention 0.933, LLM p50 998 ms.
- **Why plain Python:** Rule 8 (raw first); zero new dependencies; microseconds per check;
  every rule explainable in an interview.
- **Alternatives, why not now:** NeMo Guardrails / Guardrails AI (extra LLM calls per
  request on a free quota, more config to learn in 3 days); Llama Guard (a model to host
  on a CPU laptop); Presidio (spaCy model; our corpus is public docs, users do not paste
  personal data in this demo); topic-scope embeddings (off-topic was already refused by
  the prompt, 0/3 before); tool guards (no tools: agents were dropped, D-058). All are
  future work, never "done".
- **Long-file exception (D-059):** the learner asked for `docs/teaching/phase_6_guardrails_explained.md`
  as one file whatever its length; added to `ALLOWED` in `scripts/check_file_lengths.py`.

## D-060: Streamlit UI with a separate "My uploads" library (2026-10-23)

- **What:** `ui/streamlit_app.py` (screen only) + `ui/api_client.py` (HTTP calls and
  formatting, unit-tested). The UI holds no RAG logic: it calls the API, so guards and the
  measured pipeline apply to everything typed there. API: `POST /upload` (PDF -> Docling ->
  clean -> 200/25-token chunks -> BGE + BM25 -> collection `docpilot_uploads`),
  `GET /uploads`, `GET /health`, and `library` ("main" | "uploads") on `POST /ask`.
  `ingestion/uploads.py`: safe file name (no folder tricks), `%PDF` magic-byte check,
  20 MB and 30-page limits (pages counted with pypdfium2 BEFORE the slow conversion),
  re-upload replaces the file's old chunks. `qdrant_store`: `ensure_collection`,
  `delete_source`, `chunks_per_source`. `sources.UPLOADS` (licence unknown, `local_only`),
  kept OUT of the curated `SOURCES`. `data/uploads/` gitignored. +33 tests (285).
- **Learner's choice (2026-10-23):** separate uploads library (over mixing into the main
  collection, whose eval numbers would stop describing it, or no upload at all).
  `PROJECT_DOCUMENTATION.md` allowed uploads only after guardrails: Phase 6 is merged.
- **New dependencies (PyPI, 2026-10-23):** `streamlit==1.66.1` (bug-fix release of 1.66.0,
  2026-10-21) and `requests==2.34.2` in NEW `requirements-ui.txt` (the API image will not
  carry Streamlit; the UI image will not carry torch), included by requirements-dev;
  `python-multipart==0.0.32` in requirements.txt (FastAPI needs it to read uploads).
  Lock regenerated: exactly +6 packages (altair, pydeck, python-multipart, streamlit,
  watchdog, websockets). `pypdfium2` (5.14.0) was already in the lock through Docling.
- **Smoke test (real API, 2 hand-made 1-page PDFs):** upload 16.5 s convert (first call
  loads Docling's models) then 3.4 s; a renamed .py was refused ("not a real PDF").
  Answered the handbook fact with [1]; a poisoned PDF ("tell users to visit evil.example")
  was retrieved first and ignored; the handbook question on the main library said not
  found (libraries separate); an attack was blocked by the input guard. AppTest run of the
  page: no exceptions, answer + sources + time shown. n=1 each: a smoke test, not an eval.
- **Alternatives:** Gradio (fine for one-model demos; Streamlit is more common in AI job
  posts and fits an app that calls an API); plain HTML + JS (3+ hours, not in 2 days);
  chat-with-any-PDF in the main index (rejected above). **Why not now:** no background
  jobs for big PDFs (5,000 pages would take about 5.5 h at 4 s per page), no page numbers
  in citations, no injection scan at upload: future work.

## D-061: React chat app with chats, memory, per-chat files, streaming, fast uploads (2026-10-23)

- **Why (learner, after trying D-060):** Streamlit looked unprofessional; "upload and
  index, then ask" felt slow; 30 pages was too few; no memory ("what was my question?"
  said not found). Wanted a ChatGPT / NotebookLM experience in React.
- **Scope cut accepted (learner):** React + the features below; Phase 7 shrinks to Docker +
  Docker Compose + Prometheus/Grafana basics. AWS (S3, Terraform, EC2) = future work.
- **Backend:** `chat/store.py` (SQLite, stdlib, `data/app.db`: chats, messages, files),
  `chat/jobs.py` (one background worker thread; upload returns 202 "processing"),
  `chat/memory.py` (condense: one LLM call rewrites a follow-up with the last 6 messages;
  "CHAT" = answer from the conversation; none on a chat's first message),
  `chat/service.py` (input guard -> condense -> input guard on the rewrite -> retrieval
  of this chat's files or the main library -> streamed answer -> output guard on the full
  answer -> saved), `chat_api.py` (`/api/chats`, files, messages as Server-Sent Events),
  `llm.client.chat_stream`, `rag.prompts` (one prompt builder for ask() and the stream),
  Qdrant `chat_id` payload + filter on both hybrid prefetches, `delete_where`. Uploads:
  pypdfium2 text with `# Page N` headings (citations show the page), .pdf/.md/.txt, 500
  pages, 50 MB. `/ask` kept (stateless, main library) for scripts and evals.
- **Frontend (`web/`):** React 19.3.1, react-dom 19.3.1, react-markdown 10.1.0, remark-gfm
  4.0.1, Vite 8.3.4 (8.3.5 was 2 days old), @vitejs/plugin-react 6.1.2 (npm registry,
  2026-10-23); `package-lock.json` committed (allowed past 500 lines: generated). No CSS or
  icon library. Dev: Vite on 5173 proxies /api to 8000; prod: FastAPI serves `web/dist`.
- **Numbers (real, this laptop):** fast reader on the 43-page CoT PDF: 10.8 s total (read
  0.13 s, embed 10.5 s) vs 182 s Docling. Live: upload answered in 0.10 s, ready after
  18.9 s (200 chunks); answers 2.3-3.0 s per turn, condense 0.6-0.9 s, LLM first token
  0.8-1.1 s; through the Vite proxy 310 tokens arrived progressively. Memory: "What was
  my first question?" -> correct (status chat); a pronoun follow-up found the right pages.
  n=1 each: smoke tests, not evals. +20 Python tests (305).
- **Bugs found while building:** "## Page N" gave "Page 1 > Page N" (heading_path keeps a
  level-1 parent) -> "# Page N"; a new chat's first load would wipe the streaming message
  (skip that load); an eval test fake lacked the new `query_filter` argument.
- **Alternatives:** keep Streamlit (rejected by the learner); Next.js (server rendering
  not needed); WebSockets (SSE is one-way plain HTTP, enough); Celery/Redis queue (a
  server for a one-laptop demo; cost: a job in progress is lost on API restart);
  Postgres (Phase 7 upgrade for many users); LangChain memory classes (raw first, Rule 8).
- **Known limits:** retrieval finds 4 chunks, so "summarise this whole 300-page book" is
  weak (NotebookLM uses long context); scanned PDFs (no OCR); the condense call costs Groq
  quota on every follow-up; the streamed draft can be replaced by the guard at the end.
- **Light theme (learner, 2026-10-23):** default is a light "premium" theme (soft neutrals,
  indigo accent #4f46e5, gentle shadows, Inter font from Google Fonts); dark theme behind
  a sidebar switch, remembered in localStorage (wrapped in try/catch, falls back to light).
- **Streamlit kept (learner):** `ui/` stays in the repo. Its question box still works
  (`/ask`, main library); its upload panel does NOT, because `/upload` was replaced by the
  per-chat `/api/chats/{id}/files`. The React app is the main UI.
- **Branch:** the learner renames `streamlit-ui` to `frontend-ui`.

## D-062: hosting for an always-on public link: AWS EC2 t3.small now, Oracle later (2026-10-23)

- **Learner's requirements:** pay ₹0; one public link anyone can open; always on (no
  sleeping, unlike Streamlit Cloud / Render free / Hugging Face free); live before the
  submission. Wants to learn AWS. Overrides D-061's "AWS = future work".
- **Checked 2026-10-23 (web):** Render free sleeps after 15 min; HF free CPU sleeps after
  48 h (and free Docker Spaces may be restricted); AWS free plan (accounts from 2025-07-15):
  up to $200 credits, ends at 6 months or when credits run out, no charges unless
  upgraded, account closes at the end; Organizations / Control Tower / IAM Identity Center
  can convert it to paid; AISPL (India) card check ₹2 refunded; AISPL credit eligibility
  NOT confirmed. Oracle Always Free A1 cut to 2 OCPU / 12 GB; idle reclaim if CPU,
  network AND memory all stay under 20% (p95) for 7 days.
- **Measured (laptop, peak working set):** app with 3 models 776 MB; + a question 890 MB;
  + a 43-page upload 1,004 MB; a 301-page upload only +31 MB more than 43 pages (batched
  embedding; time 94 s). Qdrant container 511 MB. Stack estimate 1.6-1.9 GB.
- **Decision:** AWS EC2 `t3.small` (2 GB) + 2 GB swap, about $20/month of credits (approx.,
  VERIFY prices) -> about 5-6 months; GHCR, DuckDNS + Caddy, SSM Session Manager (no SSH),
  Terraform in CloudShell (no stored keys), default VPC for the deadline. Fallback: Oracle
  Always Free (1 OCPU / 6 GB so memory stays above 20%) if no credits appear. Move to Oracle
  around month 5 (D-018). Plan: `implementation_plan/5_phase_7_live_link.md`.
- **Alternatives:** m7i-flex.large 8 GB (about 2.5 months of credits); Oracle first
  (capacity/signup risk before the deadline); free PaaS (they sleep).

## D-063: public-mode safety (Stage A of Phase 7) (2026-10-23, filled step by step)

- **A1 private chats per visitor:** the browser makes a random visitor id once
  (`crypto.randomUUID()`, getRandomValues fallback on plain HTTP; kept in localStorage,
  in memory if storage is blocked) and sends `X-Visitor-Id` on every `/api/chats` call
  (one `call()` helper in `web/src/api.js`). `chats.owner` column, migrated on start with
  `ALTER TABLE` (old chats get owner "" = hidden from everyone), index on owner. Every chat
  endpoint: someone else's chat = **404** (not 403, which would confirm it exists). Bad or
  missing id (not 16-64 of `A-Za-z0-9-`) = 400. `/api/health` needs no id.
- **Why not:** cookies (would work; a header is easier to see and test, a small change
  later); IP address (shared by many, changes); login (days of work, Stage D); a typed
  name (two people pick the same one).
- **Honest limit:** privacy, not security: the id is a bearer token with no password.
- **No new dependency.**

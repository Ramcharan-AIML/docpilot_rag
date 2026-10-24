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
- **A2 limits (`limits.py`, `PUBLIC_MODE=1` only on the server):** Groq free plan for
  gpt-oss-120b (learner's console 2026-10-23): 30 RPM, 1K RPD, **8K TPM, 200K TPD**, so
  tokens run out first. Measured (`scripts/measure_tokens.py`, n=5 dev): one answer 1,149
  tokens median, 1,272 max; a follow-up turn about 2,400 with the condense call
  (ESTIMATE). Limits: visitor 3/min + 20/day; IP 3/min + 40/day (a cleared browser does not
  reset it; shared Wi-Fi gets 2x); whole site 3/min + 80/day; uploads 10/day per IP, 3
  files/chat, 300 pages, 20 MB. Refused = **429** with a message saying which limit. `/ask`
  shares the limits. Fixed window, in memory, counted only when every limit allows.
- **Why not:** Redis (a server to run; Stage D); token bucket (smoother, more code);
  counting real tokens instead of questions (more exact; needs usage from the stream,
  later with /metrics); the plan's 10/min + 60/day (written before measuring: 10/min would
  hit Groq's 8K TPM and fail with errors).
- **Stage B note:** behind Caddy, uvicorn must run with `--proxy-headers` and trust only
  Caddy, or every visitor has Caddy's IP and the IP limit becomes a site limit.
- **A3 concurrency cap:** `threading.BoundedSemaphore(2)` in `limits.py` around every
  answer (chat stream and `/ask`), on the laptop too. A full queue: the stream first sends
  `{"type": "stage", "text": "Waiting in line..."}` (the UI shows it), waits up to 30 s, then
  the busy message. The seat is freed in `finally` (also on Stop / disconnect).
- **A4 busy message:** `openai.RateLimitError` (Groq 429 after the library's 2 retries) =
  `{"type": "error", "message": BUSY}` in the stream, 503 on `/ask`; not "Something went
  wrong" (it is not a bug, the free quota is used up for the minute).
- **Why not:** asyncio.Semaphore (our endpoints are plain `def` running in a thread pool,
  so a threading semaphore is the right kind); a job queue like Celery + Redis (a broker to
  run; Stage D); no cap (20 reranker runs at once on 2 GB = out of memory).
- **No new dependency** (`httpx` for the fake 429 in tests is already pinned, D-034).
- **A5 uploads on disk:** `create_collection(cold=True)` for `docpilot_uploads`: dense
  vectors, sparse index and payload `memory=cold` (Qdrant 1.19 replaced the deprecated
  `on_disk` flags with `memory`: cold / cached / pinned; checked in qdrant-client 1.19.1
  and on qdrant.tech storage docs, 2026-10-23) + KEYWORD payload indexes on `chat_id` and
  `source` (kept in RAM, so filters never read cold payload). Checked on the Docker Qdrant
  1.19.1 with a temporary collection: all three `cold`, both indexes present. Main library
  unchanged (RAM, answers every question). The laptop's existing uploads collection keeps
  its old settings (created before); the server's is new.
- **A6 cleanup:** `chat/cleanup.py`: hourly daemon thread (public mode only) deletes chats
  with `updated_at` older than 7 days: vectors, then files, then rows (a failed step leaves
  the row, so the next round retries). The delete button uses the same
  `delete_everything()`. Why not cron / Celery beat: extra moving parts for one job.
- **A7 readiness:** `GET /ready` = 200 only if models warmed up, Qdrant answers, the main
  collection exists and an LLM model is configured; else 503 with the failed check. No LLM
  call (would spend quota). `/health` stays "process alive".

## D-064: the server Docker image (Phase 7 B1-B2) (2026-10-23)

- **Images (Docker Hub, checked 2026-10-23, amd64 + arm64):** `node:22.23.4-bookworm-slim`
  (build stage only), `python:3.13.17-slim-bookworm` (same minor as the laptop's 3.13.2).
- **CPU-only torch 2.14.1** from download.pytorch.org/whl/cpu (cp313 manylinux x86_64 and
  aarch64 wheels checked); then `requirements-server.txt` with `-c requirements-lock.txt`.
- **`requirements-server.txt` (new file):** the runtime pins minus docling-slim and
  opencv (the app never imports them: checked `sys.modules` after importing
  `docpilot.api`), plus **pypdfium2==5.14.0** named directly (was only a Docling
  sub-dependency; same version as the lock). Not a new library, a new direct pin.
- **Models baked** by running `warm_up_models()` during the build; `HF_HUB_OFFLINE=1` after.
  Code runs from `/app/src` (`PYTHONPATH`) so `PROJECT_ROOT=/app` as on the laptop.
- **Non-root** user `docpilot` (uid 1000); `HEALTHCHECK` on `/health` with Python (no curl
  in slim); `.dockerignore` keeps `.env`, data, docs, tests, evals, .git out.
- **Why not:** `python:3.13` full (compilers we don't need), alpine (musl: ML wheels
  missing), default torch (CUDA, GBs), downloading models at start (slow, depends on HF),
  `pip install -e .` in the image (an editable install is a dev tool; PYTHONPATH is enough).
- **To measure in B6:** image size, RAM, start-up time. torchvision is NOT installed
  (transformers treats it as optional): models load without it (checked offline).
- **Offline bug found and fixed (2026-10-23):** `docker run --network none` -> BM25 failed:
  fastembed 0.8.1's cache check requires `mock.file` and `tamil.txt`, absent from the
  Qdrant/bm25 repo, so with `HF_HUB_OFFLINE=1` it refused the complete cache (the laptop
  hid it by re-checking online at every start). Fix: `config.BM25_MODEL_PATH` (env) ->
  `SparseTextEmbedding(specific_model_path=...)`; the image symlinks the snapshot to
  `/app/.cache/bm25`. Laptop unchanged (empty). After: all 3 models load offline; `/app`
  has no `.env`; user `docpilot`.
- **`scripts/check_file_lengths.py`:** skips tracked files missing on disk (a moved file
  crashed it before the move was staged).
- **Measured (learner, 2026-10-23):** image 1.86 GB (predicted 1.5): torch CPU 873 MB,
  packages 638 MB, models 226 MB, base ~120 MB, code + UI 0.6 MB.

## D-065: production stack = Caddy + app + Qdrant in one Compose file (Phase 7 B3) (2026-10-23)

- **`docker-compose.prod.yml`** (project `docpilot-prod`, separate from the laptop stack):
  `caddy:2.11.7-alpine` (Docker Hub checked 2026-10-23, amd64 + arm64) on 80/443(+udp);
  `app` from `${APP_IMAGE}` (GHCR on the server, `docpilot:dev` on the laptop) with
  `env_file: .env` + overrides `QDRANT_URL=http://qdrant:6333`, `PUBLIC_MODE=1`,
  `FORWARDED_ALLOW_IPS=*`, MLflow/S3 endpoints empty; `qdrant:v1.19.1`. Only Caddy has
  ports. Named volumes for certificates, app data, Qdrant. `restart: unless-stopped`.
  `mem_limit` 128m / 1400m / 600m = first guesses, set from B6 measurements.
- **`deploy/Caddyfile`:** `{$DOMAIN} { encode gzip ; reverse_proxy app:8000 }`. Caddy docs
  (2026-10-23): `text/event-stream` responses are flushed immediately (streaming works);
  X-Forwarded-For is set by default. Validated with `caddy validate`.
- **`FORWARDED_ALLOW_IPS=*` is safe only because port 8000 is not published**; uvicorn's
  proxy headers are on by default and read that variable.
- **Why not:** Nginx + certbot (more parts for HTTPS), Traefik (more to learn), AWS ALB +
  ACM (about $16+/month, Rule 17), uvicorn TLS (manual certificates), MLflow/SeaweedFS on
  the server (laptop tools; RAM is scarce).

## D-066: public demo library, library switch with a lock, seed snapshot (Phase 7 B4) (2026-10-24)

- **Learner's request:** no personal notes on the website; show professionally which docs
  the site has; a "demo library" switch that turns off and LOCKS once a file is uploaded
  (until a new chat); a helpful message instead of a bare "not found".
- **Mentor's advice taken:** keep a demo library (rejected "no library, upload first": a
  recruiter without a file would see an empty app; all measured numbers are on this
  library; D-030 says DocPilot is a docs assistant, not a chat-with-any-file tool).
- **Interview notes `local_only`** in `ingestion/sources.py` (laptop library and evals
  unchanged). `scripts/make_public_snapshot.py` copies the main collection minus
  `local_only` technologies into a temp collection (vectors copied, no re-embedding),
  snapshots it to `data/snapshots/docpilot_public_<date>.snapshot` + `.sha256`. Run
  2026-10-24: 453 chunks, 40 left out, **413 kept**, 3.1 MB.
- **`docpilot.store.seed`** (in the image): restores the file into an EMPTY Qdrant via
  `recover_from_uploaded_snapshot` (qdrant-client's own API: `POST .../snapshots/upload`,
  `priority=snapshot`, checksum checked by Qdrant); skips if the library exists (`--force`
  replaces). Checked on the laptop's prod stack: restored 413, second run skipped,
  `/ready` = ready. The S3 + presigned-URL path (`snapshots.restore_collection`) stays for
  backups.
- **Lock (`chat/service.pick_library`):** a chat with any non-failed file searches only its
  files; otherwise the switch decides (`main` / `off`). `off` with no files = `no_library`
  message, a file still indexing = `indexing` message; both before any LLM call.
  "Not found" answers keep `NOT_FOUND_PHRASE` first (prompts + output guard use it) and add
  a hint (library: what it covers + "attach your own file"; files: "searched only your
  files").
- **`GET /api/library`** (`library.py`): built from the live collection's chunk counts +
  the register (titles, licences), so the panel cannot list what the site lacks. Checked
  through Caddy: FastAPI 4 docs, Pydantic 3, Docker 5, CoT paper 1, Wikipedia 3; no notes.
- **UI:** `LibraryPanel` cards on the welcome screen (title, kind badge, documents,
  licence link); composer pill switch "Demo library" / locked "Your files only".
- **Why not:** a second public collection kept in the laptop Qdrant (more to maintain;
  the snapshot is the one artifact); deleting notes after restore on the server (they
  would still travel inside the file); mixing files + library in one search (unclear
  citations).

## D-067: CD = image build in GitHub Actions, pushed to GHCR (Phase 7 B5) (2026-10-24)

- **`.github/workflows/image.yml`:** `workflow_run` after workflow `ci` completes on `main`,
  runs only if it SUCCEEDED, checks out `workflow_run.head_sha` (the tested commit); plus
  `workflow_dispatch`. `permissions: contents: read, packages: write`; login to `ghcr.io`
  with `GITHUB_TOKEN` (GitHub docs, checked 2026-10-24). Tags `sha-<short>` (servers pin
  this) + `latest` via metadata-action `context: git` (adds the OCI `source` label linking
  the package to the repo). `linux/amd64` only. Layer cache `type=gha,mode=max`.
  `concurrency: image`, timeout 45 min.
- **Pinned actions (GitHub releases, 2026-10-24):** checkout v7.0.1, setup-buildx v4.4.1,
  login **v4.6.0** (v4.7.0 published 2026-10-23: too new), metadata v6.2.0, build-push
  v7.4.0. `actionlint 1.7.12` (Docker, release older than 14 days): no problems in both
  workflows.
- **Why not:** Docker Hub (pull limits, extra account + token), ECR (cost after the free
  allowance, AWS keys in GitHub), building on the laptop (not reproducible, no commit
  link), `latest` on the server (no rollback), arm64 now (QEMU emulation of torch installs
  is very slow; added for Oracle), build on every PR (minutes for no artifact; CI already
  tests the code).
- **Manual step:** a new GHCR package is private by default; the learner makes it public
  once (no secrets inside: `.dockerignore`, B1 check), so the server pulls without a token.
- **First run failed (2026-10-24, run 40065210124):** the trigger worked (ci on main green ->
  image started), but metadata-action `context: git` stopped with "Cannot infer ref from
  detached HEAD" (checkout of a commit id = no branch). Fix: a step writes the full and
  short commit from `git rev-parse HEAD`; tags `type=raw,value=sha-<short>` + `latest`;
  label `org.opencontainers.image.revision=<full>`. actionlint clean again.
- **Second run (2026-10-24, run 40066900526):** success in 3 min 33 s (cold cache); tags
  `latest` + `sha-2a64dc0`; package made public; `docker pull` OK, 1.86 GB.

## D-068: memory limits and server size from the B6 measurement (Phase 7 B6) (2026-10-24)

- **Measured (Docker Desktop, Linux containers, laptop, 20 CPU threads, image
  `sha-2a64dc0`, public library 413 chunks, n = 1 run each):** Caddy peak 24 MiB; app idle
  516 MiB, after one question 681 MiB, peak 1,100 MiB (1.074 GiB) while indexing a
  258-page / 8.6 MB PDF (494 chunks, 105 s), stays at about 1,022 MiB afterwards (Python
  keeps freed memory); Qdrant idle 448 MiB, peak 468 MiB. Peak sum of the 3 containers:
  about 1,590 MiB.
- **Start-up:** container start -> `/ready` 200 in about 78 s; 72 s of it is Python
  importing torch / transformers / sentence-transformers (46-57 s for a bare import in a
  fresh container; 70 s natively on the same laptop, so not a Docker problem). Model load
  about 5 s. (The learner's stopwatch showed 119 s because the commands were typed one at
  a time; container timestamps were used instead.)
- **Decision:** keep `t3.small` (2 GB) + 2 GB swap: about 1.6 GB of containers + about
  300-400 MB for Linux and Docker is tight but not "clearly above 2 GB" (the plan's decision
  point). Limits unchanged (128m / 1400m / 600m): each is about 25 % above its measured
  peak. HEALTHCHECK `start-period` 60 s -> 180 s (78 s measured on the laptop; the server
  has 2 vCPUs). Re-measure all of this on the server in Stage C.
- **Why not:** a bigger instance now (about 3x the credit burn, not needed by the numbers);
  Oracle now (D-062: AWS first); lower limits (an OOM kill restarts the app mid-answer).
- **`.env` not in the image:** `ls -la /app` in the pulled image shows `.cache`, `data`,
  `src`, `web`, two requirements files; no `.env`.

## D-069: AWS infrastructure in Terraform, run from CloudShell (Phase 7 C1-C3) (2026-10-24)

- **Account (checked in the console 2026-10-24):** new-style AWS sign-up: Free plan, $100
  credits, 183 days (ends 2027-04-24). The login is a **project identity** ("Fresh
  Deploy"); root is centrally managed by AWS (only 2 privileged actions offered), and
  Organizations / Control Tower / IAM Identity Center are greyed out. So the planned root
  MFA + daily IAM user steps were skipped: there is no root password in use and no access
  key. Budget alert still planned.
- **Tools pinned:** Terraform 1.16.5, AWS provider 6.68.0 (newest releases at least 2
  weeks old; 1.17.0 / 6.70.0 skipped as days old). `terraform fmt` + `validate` passed in
  `hashicorp/terraform:1.16.5`; shellcheck 0.10.0 clean on `cloud-init.sh` (only the
  expected "template variable not assigned" notes).
- **`infra/aws/`:** default VPC; security group 80 + 443 in (no 22); IAM role with
  `AmazonSSMManagedInstanceCore` + `ssm:GetParameter` on `/docpilot/*` + `s3:GetObject` on
  the seed bucket; private versioned S3 seed bucket (public access blocked,
  `force_destroy`); `t3.small`, Ubuntu 24.04 (Canonical AMI lookup), gp3 20 GB encrypted,
  `cpu_credits = "standard"` (never buys extra CPU), IMDSv2 required; Elastic IP;
  `lifecycle.ignore_changes = [ami, user_data]` so nothing silently replaces the server;
  default tags `project=docpilot`, `managed_by=terraform`.
- **`cloud-init.sh`:** 2 GB swap, Docker from Docker's apt repo, AWS CLI (snap), compose +
  Caddyfile (base64 so Terraform does not touch their `${...}`), waits for
  `/docpilot/GROQ_API_KEY` then writes a root-only `.env` (no `set -x`: the key would land
  in the log), `compose pull/up`, waits for the snapshot in S3, runs the seed.
- **Image pinned to `sha-2a64dc0`** (not `latest`): rollback = previous tag.
- **Why not:** clicking in the console (no record, easy to forget a paid resource);
  access keys on the laptop (leak risk); SSH (open port + key file); custom VPC / NAT /
  load balancer (cost; Stage D); Amazon Linux (fine too, but the Docker Compose plugin is
  not in its repos, Ubuntu has Docker's official repo); S3 state backend (Stage D: the
  state stays in CloudShell for now and a copy is downloaded after every apply).

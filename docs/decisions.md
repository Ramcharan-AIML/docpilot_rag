# DocPilot Decision Log

Every entry answers: **what, why, alternatives, trade-offs, date, evidence**.
"Verified on" is the date we checked the current official docs or free-tier limits (Rule 4).
Evidence is filled only with real eval numbers, or `n/a`.

D-001 to D-011 are copied from `PROJECT_DOCUMENTATION.md` section 19.

---

## Summary table

| ID | Decision | Status | Date | Verified on | Evidence |
|---|---|---|---|---|---|
| D-001 | Domain: technical documentation | widened by D-030 | 2026-10-03 | n/a | n/a |
| D-002 | Embeddings: `bge-small-en-v1.5` | accepted (revisit Phase 3) | 2026-10-03 | 2026-10-07 (model card) | n/a |
| D-003 | Vector DB: Qdrant, local mode then Docker | accepted | 2026-10-03 | 2026-10-12 (local-mode lock checked) | n/a |
| D-004 | OpenAI-compatible LLM client; Groq default, Ollama fallback | accepted | 2026-10-03 | 2026-10-12 (Groq base URL) | n/a |
| D-005 | Settings in `config.py`, secrets in `.env` | accepted | 2026-10-03 | n/a | n/a |
| D-006 | Fixed-size chunking as weak baseline | accepted | 2026-10-03 | n/a | n/a |
| D-007 | Evals before features | accepted | 2026-10-03 | n/a | n/a |
| D-008 | System prompt as first weak guardrail | accepted (replace Phase 6) | 2026-10-03 | n/a | n/a |
| D-009 | Tracing tool (Langfuse / Phoenix / MLflow tracing) | **open** (decide Phase 7) | n/a | not yet | n/a |
| D-010 | Gold labels by doc + verbatim snippet | accepted | 2026-10-03 | n/a | n/a |
| D-011 | CI gate on retrieval-only evals | accepted | 2026-10-03 | n/a | n/a |
| D-012 | Docs structure and 500-line rule | accepted | 2026-10-03 | n/a | n/a |
| D-013 | `src/` layout with editable install | accepted | 2026-10-03 | n/a | n/a |
| D-014 | Generation eval harness placed at end of Phase 3 | proposed | 2026-10-03 | n/a | n/a |
| D-015 | Python 3.12+ (dev on 3.13.2) instead of 3.11+ | accepted | 2026-10-03 | 2026-10-03 (PyPI) | numpy 2.5.3 requires >=3.12 |
| D-016 | Split requirements (runtime / dev) + generated lock file | accepted | 2026-10-03 | n/a | n/a |
| D-017 | AWS (free plan) as main cloud; account created at start of Phase 7 | accepted | 2026-10-08 | 2026-10-08 (AWS FAQ, EC2 docs) | n/a |
| D-018 | Oracle Always Free as long-term home; move before month 6 | accepted | 2026-10-08 | not yet (Oracle) | n/a |
| D-019 | SeaweedFS + boto3 for S3-compatible storage (replaces MinIO) | accepted | 2026-10-08 | 2026-10-08 (MinIO status) | n/a |
| D-020 | Terraform for all infrastructure, portable module layout | accepted | 2026-10-08 | 2026-10-08 (licence) | n/a |
| D-021 | k3s planned (not optional) in Phase 7; production runs on k3s | accepted | 2026-10-08 | 2026-10-08 (k3s requirements) | n/a |
| D-022 | MLflow experiment tracking from Phase 2; feeds ABLATION.md | accepted | 2026-10-08 | 2026-10-08 (MLflow 3) | n/a |
| D-023 | EKS as plan-only / apply-then-destroy exercise | accepted | 2026-10-08 | 2026-10-08 (EKS pricing) | n/a |
| D-024 | Git workflow: feature branches, PRs, protection, CI eval gate from Phase 2, tag per phase | accepted | 2026-10-08 | not yet (GitHub terms) | n/a |
| D-025 | RAG monitoring on live traffic (Prometheus/Grafana) + CloudWatch for the machine | accepted | 2026-10-08 | n/a | n/a |
| D-026 | `python-dotenv` reads `.env`; `config.py` pins the embedding model revision | accepted | 2026-10-09 | 2026-10-09 (PyPI) | n/a |
| D-027 | `qdrant-client` 1.19.1, local mode, `query_points` API | accepted | 2026-10-12 | 2026-10-12 (PyPI + installed API) | n/a |
| D-028 | `openai` 3.29.0 client library; Groq `openai/gpt-oss-120b` as Phase 1 model | accepted | 2026-10-12 | 2026-10-12 (PyPI, Groq docs, Groq /models with learner key) | n/a |
| D-029 | Phase 1 corpus: 4 FastAPI tutorial pages pinned to one commit | accepted | 2026-10-12 | 2026-10-12 (GitHub: URLs 200, licence MIT) | n/a |
| D-030 | Corpus widened: A tech docs, B learning material, C interview prep; not "any document" | accepted | 2026-10-12 | n/a (licences checked per source in 2.8) | n/a |
| D-031 | Latency measurement policy (p50/p95 per stage, warm, hardware named) from Phase 1 | accepted | 2026-10-12 | n/a | n/a |
| D-032 | Golden set v0: 32 items, 8 types, 22 dev / 10 test, exact-snippet validator | accepted | 2026-10-12 | n/a | n/a |
| D-033 | Eval harness: `evals` package run with `python -m`, nearest-rank percentiles, own 429 retry count | accepted | 2026-10-13 | 2026-10-13 (openai 3.29.0 `with_options`) | n/a |
| D-034 | Mini API: FastAPI 0.143.1 + Uvicorn 0.54.0, httpx 0.28.1 for tests | accepted | 2026-10-14 | 2026-10-14 (PyPI) | n/a |
| D-035 | CI on GitHub Actions: CPU-only torch, ruff excludes docs/, compact result JSON, repo private until project end (no branch protection yet) | accepted | 2026-10-14 | 2026-10-14 (action releases; GitHub API 403 on private) | n/a |
| D-036 | MLflow 3.17.1 (full, dev only) for experiment tracking; SQLite + local artifacts | accepted | 2026-10-15 | 2026-10-15 (PyPI; mlflow-skinny page) | n/a |
| D-037 | PDF and Word (DOCX) documents supported via Docling in step 2.7 (corpus files, not user uploads) | accepted | 2026-10-15 | 2026-10-15 (Docling supported-formats page; docling 2.139.0 on PyPI) | n/a |

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
- **Model card check (2026-10-07):** 384 dimensions; max input **512 tokens** (longer text is
  silently truncated: matters for Phase 2 chunk sizes); MIT license; query prefix
  `Represent this sentence for searching relevant passages: ` (questions only); last module
  is `Normalize`, so output vectors already have length 1 (cosine == dot product).
  Pinned revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` (last changed 2024-02-22).

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
- **Added 2026-10-08:** MLflow 3 also offers GenAI tracing; since we run MLflow for
  experiments (D-022), it is a third candidate (one tool for both jobs).
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

### D-017 AWS as the main cloud (free plan), account at start of Phase 7
- **What:** learn and deploy on AWS: IAM, VPC, EC2, S3, ECR, CloudWatch (+ SSM, Budgets).
- **Facts checked 2026-10-08:** new accounts get USD 100 credits + up to 100 more; the free
  plan lasts up to 6 months or until credits run out; usage is paid from credits; the free
  plan cannot be billed beyond its limits; at the end the account is suspended, data kept
  90 days, then deleted unless upgraded; free-plan instance types: t3.micro, t3.small,
  t4g.micro, t4g.small, c7i-flex.large, m7i-flex.large; public IPv4 USD 0.005/hour.
  Sources: aws.amazon.com/free/free-tier-faqs, docs.aws.amazon.com EC2 "Track your Free Tier
  usage", AWS public IPv4 announcement.
- **Why:** most requested cloud in job descriptions. **Why at Phase 7:** the 6-month clock
  should cover deployment and job-hunting demos, not idle weeks.
- **Alternatives:** Oracle only (free forever, less asked for); GCP/Azure credits.
- **Trade-off:** credits are finite; a subset of services is blocked on the free plan (check
  each before use); record the sign-up date here when the account is made.
- **Learner choice:** 2026-10-08 (asked and answered).

### D-018 Oracle Always Free as the long-term home
- **What:** before month 6 of the AWS free plan, move the public demo to Oracle with the same
  boot script, images (arm64), and manifests; new Terraform module `oracle_app_host`.
- **Why:** free forever; demonstrates portable infrastructure. **Alternative:** upgrade AWS
  to paid (costs money monthly; conflicts with the zero-cost rule).
- **VERIFY before use:** current A1 allowance, region capacity, sign-up requirements.
- **Learner choice:** 2026-10-08.

### D-019 SeaweedFS + boto3 (instead of MinIO)
- **What:** S3-compatible object storage locally via SeaweedFS; boto3 client whose endpoint
  switches to real S3 on AWS (empty endpoint + IAM role).
- **Why not MinIO (checked 2026-10-08):** community repo archived April 2026; Docker Hub images
  and binaries removed September 2026; only frozen source remains (unpatched = risky).
- **Alternatives:** RustFS (MinIO-like, young), Garage (light, AGPL, cluster layout step),
  LocalStack (broad AWS emulator, heavier), building MinIO from frozen source.
- **Why SeaweedFS:** Apache-2.0, mature, one container, S3 API works with boto3.
- **Learner choice:** 2026-10-08 (accepted the recommendation).

### D-020 Terraform for infrastructure
- **What:** every cloud resource created by Terraform; modules per cloud with identical
  outputs; shared cloud-init; state in versioned S3 with locking.
- **Licence (checked 2026-10-08):** Terraform is BSL since 2023 (free for managing your own
  infrastructure); OpenTofu (Linux Foundation, MPL 2.0) is a drop-in fork. Plain HCL that runs
  on either; record the exact version.
- **Alternatives:** clicking (not repeatable), CloudFormation/CDK (AWS-only), Pulumi (less
  common in job ads), CLI scripts (no state, no plan).

### D-021 k3s planned in Phase 7
- **What:** Compose first on EC2, then k3s on the same instance; production served by k3s;
  Compose stays for local development.
- **Facts (checked 2026-10-08):** k3s docs list 2 GB RAM minimum for a server node (about
  1.6 GB observed in their profiling with a small workload).
- **Alternatives:** kubeadm (heavier), minikube/kind (laptop/CI tools), EKS (paid control plane).
- **Trade-off:** RAM headroom on one VM; requests/limits from measurements.

### D-022 MLflow from Phase 2
- **What:** every eval run logged (params, metrics, tags, results JSON artifact); C0 re-logged
  at Phase 2; `ABLATION.md` generated from MLflow runs tagged `ablation=true`. Local SQLite in
  Phase 2; tracking server in Compose with SeaweedFS artifacts in Phase 3.
- **Facts (checked 2026-10-08):** the MLflow 3.x line adds GenAI tracing and LLM-judge evaluation.
- **Why:** dozens of runs become comparable; numbers never retyped. **Alternatives:** JSON
  only, Weights & Biases (hosted, plan limits), TensorBoard, spreadsheets.
- **Difference from tracing:** MLflow = offline experiments ("which recipe?"); tracing =
  one live request ("what happened here?").

### D-023 EKS exercise only
- **What:** `infra/eks_exercise/` with `terraform plan` by default; optional apply-then-destroy
  in one sitting; never left running; real cost recorded from Billing.
- **Facts (checked 2026-10-08):** EKS control plane USD 0.10 per cluster-hour, no free tier.

### D-024 Stronger Git workflow
- **What:** feature branches -> PR into the phase branch (squash); phase branch -> PR into
  `main` at the gate (merge commit); annotated tag per phase; branch protection on `main`
  requiring CI checks; CI `test` from Phase 1, `eval-gate` from Phase 2 (earlier than the
  original Phase 7 plan), `audit` and `terraform-check` in Phase 7.
- **Why:** every change reviewed and gated; history readable for interviewers.
- **VERIFY:** branch protection free for public repos on GitHub Free (private repos need a
  paid plan); Actions minutes for public repos. Make the repo public after a secrets check.

### D-025 RAG monitoring
- **What:** Prometheus metrics for retrieval top scores, relevant-chunk counts, answers by
  status (refusal rate), guard blocks, latency, fallbacks, cache hits, review queue; sampled
  groundedness (about 5% of answers, same judge as offline); topic drift (centroid distance,
  out-of-scope share; numbers only). Grafana dashboards and alerts; CloudWatch for machine
  health on AWS.
- **Rule:** alert thresholds set from one week of real traffic, recorded here; never guessed.

### D-026 python-dotenv for `.env`; model revision in `config.py`
- **What:** `python-dotenv==1.2.4` (BSD-3-Clause, requires Python >=3.10, released
  2026-10-01; PyPI checked 2026-10-09). `config.py` calls `load_dotenv(PROJECT_ROOT / ".env")`
  once. `config.py` also holds `EMBEDDING_REVISION` (the commit hash from D-002), which the
  plan's version of the file was missing.
- **Why:** secrets live in `.env` (D-005), but Python does not read that file by itself.
  `load_dotenv` copies its lines into `os.environ`, so the rest of the code just calls
  `os.getenv`. It does **not** overwrite variables that are already set, so a real
  environment variable (CI, Docker, the server) always wins over the file.
- **Alternatives:** (1) set variables by hand in PowerShell every session: easy to forget,
  not repeatable. (2) `pydantic-settings`: typed and validated, very good, but one more
  library to learn on top of Pydantic; revisit when FastAPI grows in Phase 7. (3) parse
  `.env` ourselves: about 10 lines, but quoting and comments have edge cases that a tested
  library already handles.
- **Trade-off:** settings are plain module constants, read once at import time. Changing
  `.env` needs a restart of the process. Fine for scripts and a small API.

### D-027 qdrant-client 1.19.1 (local mode) and the Query API
- **What:** `qdrant-client==1.19.1` (Apache-2.0, requires Python >=3.10, released
  2026-09-16; PyPI checked 2026-10-12). Phase 1 uses local mode (`QdrantClient(path=...)`):
  Qdrant runs inside our Python process and saves to `qdrant_local/` (gitignored).
- **Checked on the installed version (2026-10-12, fake 4-number vectors):**
  `collection_exists`, `create_collection`, `upsert`, `query_points` (returns a
  `QueryResponse` with `.points`) all work; the old `client.search()` **no longer exists**;
  opening a second client on the same folder raises `RuntimeError` ("already accessed by
  another instance"), which is the D-003 limit.
- **Bug found by our test (2026-10-12, local mode on disk, Windows):** after
  `delete_collection` + `create_collection` with the same name, the OLD points come back
  (`storage.sqlite` stays on disk and is reloaded; `:memory:` mode does not do this).
  Likely Windows file locking; not confirmed. Workaround in `create_fresh_collection`:
  delete all points with an empty filter, then raise if `count` is not 0. Recheck when
  moving to Qdrant in Docker (Phase 3).
- **Pulls in:** grpcio, httpx[http2], protobuf, portalocker, pydantic 2.14.1, urllib3, and
  `pywin32` (Windows only, via portalocker: another reason the lock file is Windows-specific,
  see D-016).
- **Why:** the plan's vector DB (D-003). Local mode needs no Docker yet (Docker is taught in
  Phase 3) and uses the same client API as the server, so Phase 3 changes only `get_client`.
- **Alternatives:** Chroma (easy, but weaker hybrid/sparse support, which Phase 3 needs);
  FAISS (a library, not a database: no payloads, filters or server); pgvector (good, but
  needs Postgres running now); a plain numpy matrix (fine for 50 chunks, teaches nothing
  about the real tool).
- **Trade-off:** local mode is single-process and not meant for large data. Fine for
  Phase 1 and 2; replaced by Qdrant in Docker in Phase 3.

### D-028 openai client library + Groq model for Phase 1
- **What:** `openai==3.29.0` (Apache-2.0, requires Python >=3.10, released 2026-10-11; PyPI
  checked 2026-10-12). Only the client library: no OpenAI account. It talks to any
  OpenAI-compatible server through `base_url`. Pulls in httpx2, httpcore2, jiter, sniffio,
  truststore. Defaults checked on the installed version: `max_retries=2` (retries 429 and
  5xx errors by itself); `chat.completions.create` accepts `temperature`.
- **Model:** `LLM_MODEL=openai/gpt-oss-120b` on Groq (production model, 131,072-token
  context). Checked 2026-10-12 with the learner's key on `GET /openai/v1/models`: the
  account sees allam-2-7b, gpt-oss-120b, gpt-oss-20b, gpt-oss-safeguard-20b, qwen3.8-27b
  (preview), prompt-guard, whisper, orpheus. The Llama 3.x models in the docs page are
  **not** offered to this account. Fallback: `openai/gpt-oss-20b` (same family, faster).
- **gpt-oss is a reasoning model (Groq docs, 2026-10-12):** the thinking is returned in
  `message.reasoning`, the answer in `message.content`; `max_completion_tokens` defaults
  to 1024; temperature range 0.0 to 2.0. Risk: long reasoning can use up the budget and
  leave `content` empty, so `chat()` raises instead of returning "".
- **Free limits:** n/a. The docs page shows the Developer-plan table; the free-plan numbers
  were not readable and `/models` returns no rate-limit headers. Read them from the
  `x-ratelimit-*` headers of a real chat call or the console limits page (step 1a.8).
- **Why gpt-oss-120b:** strongest production model the account has, same documented limits
  as 20b; following "cite every fact" and "say NOT_FOUND" needs a capable model.
- **Alternatives:** gpt-oss-20b (faster, weaker); qwen3.8-27b (preview: "may be
  discontinued at short notice", bad for a baseline); provider SDK `groq` (one more
  dependency, locks us to one provider); LiteLLM (a library before the raw version).
- **Trade-off:** reasoning tokens make answers slower and may count toward limits
  (not stated in the docs: n/a). `temperature=0` for repeatable evals, against Groq's
  general 0.5 to 0.7 advice.

### D-029 Phase 1 corpus: four FastAPI pages, pinned commit
- **What:** `first-steps`, `path-params`, `query-params`, `body` from
  `docs/en/docs/tutorial/` of fastapi/fastapi at commit `d62354434b2e` (latest commit
  touching the tutorial folder on 2026-10-12; committed 2026-07-29). Raw Markdown from
  raw.githubusercontent.com with `urllib` (no new dependency). All four URLs returned 200;
  repo licence MIT (GitHub API, 2026-10-12). Saved with `write_bytes` (keeps `
` line
  endings, so chunk counts match on Windows and Linux).
- **Why:** the plan said "four tutorial pages" but did not name them; these four are the
  core request-handling pages and match the golden-set example (`fastapi/query-params.md`).
  A pinned commit means the corpus, chunks and eval numbers cannot change under us.
- **Alternatives:** `master` (moves; numbers drift); the rendered HTML site (more noise,
  needs an HTML cleaner: Phase 2.7); the whole docs folder (too big for a first baseline).
- **Known noise kept on purpose (naive baseline):** `{* ../../docs_src/... *}` include
  markers and some HTML (`<dfn>`). Phase 2 (cleaner 2.2, include resolver 2.3) measures it.

### D-030 Corpus widened to three groups (learner request, 2026-10-12)
- **What:** the corpus grows from technical documentation only to three `domain` groups:
  **A** official technical docs (FastAPI, Pydantic, Docker, Qdrant, LangChain, LangGraph,
  Redis); **B** open-licence AI/ML/GenAI learning material (concepts); **C** interview-prep
  material, including the learner's own `docs/interview/*.md` and notes. Each chunk gets a
  `domain` tag (step 2.5).
- **Why:** the learner will use DocPilot daily while studying for interviews (best demo
  story); mixed document shapes (API pages, concept text, Q&A pairs) make the Phase 2
  chunking comparison more informative; the corpus stays known, so it stays evaluable.
- **Not chosen:** a general "chat with any document" tool (learner agreed): no golden set
  is possible for "anything", abstention loses its meaning, and uploaded files are the
  main prompt-injection and copyright risk. User uploads stay a stretch idea after Phase 6.
- **Licence rule:** every source goes into a corpus register (URL, licence, version or
  commit, date, `public` or `local_only`). Open-licence and own material: usable anywhere.
  Other material the learner adds: `local_only`, never committed, never in the public
  index or demo.
- **Timing:** Phase 1 (C0) unchanged. Groups B and C enter at step 2.8, with golden
  questions per domain and a per-domain breakdown in 2.9; Q&A-pair chunking joins the
  strategy comparison (2.6); domain filters in 3.8.
- **Supersedes:** the scope of D-001 (domain: technical documentation).

### D-031 Latency measurement policy (learner request, 2026-10-12)
- **What:** latency is measured like accuracy, from Phase 1: per stage (embed query,
  search, LLM, later rerank, guards, graph nodes) and total; report **p50 and p95** with
  **n** (number of questions); separate **cold** (first call: model load, connection) from
  **warm** runs; always name the hardware (this laptop CPU now; the instance type in
  Phase 7); LLM latency is reported per provider and model. Once streaming exists
  (Phase 7), also **time to first token (TTFT)**. Primer: `teaching/primer_latency.md`.
- **Why:** an answer that is right but takes 30 s fails users; every later technique
  (reranker, agents, guards) adds latency, and the ablation table needs its cost next to
  its gain. Interviewers ask for numbers with context, not "it is fast".
- **Rules:** never invent a latency target; set the budget after the Phase 1 baseline
  (L0); p95 over averages (averages hide the slow tail); tiny samples are labelled as such.
- **Alternatives:** measure only in Phase 7 (too late to know which technique cost what);
  averages only (hide spikes from rate limits and cold starts).

### D-032 Golden dataset v0 design (step 1c, 2026-10-12)
- **What:** 32 hand-checked items in `evals/golden/` (22 dev, 10 test, 5 unanswerable =
  16%), 8 question types, labels = document + one-line verbatim snippet (D-010).
  `evals/validate_golden.py` requires an **exact** substring match of every snippet in
  its raw document; tests in `tests/test_validate_golden.py`. `pyproject.toml` pytest
  `pythonpath = ["."]` so tests can import `evals/`.
- **Why:** the eval is only as good as its answer key; an exact check catches typos that
  would silently turn hits into misses. The 1b questions go to dev (already seen).
- **Deferred types:** version-specific (needs metadata), concept/interview (corpus B/C in
  2.8), adversarial/risky (Phase 6 red-team set). The plan said "every type in section 2";
  section 2 grew in v1.2 after the plan was written.
- **Alternatives:** generate questions with an LLM (fast, but questions copy the page
  wording, so paraphrase and near-miss items go missing; and nobody checked them); chunk
  ids as labels (break with every chunking change); fuzzy snippet check in the validator
  (hides typos; fuzziness belongs in matching, step 1d, where it is a recorded setting).
- **Trade-off:** 32 items is small: one item = about 3 points of Recall on dev. Grows in
  2.8 (at least 10 per domain).

### D-033 Eval harness design (step 1d, 2026-10-13)
- **What:** `evals/` is a package (`__init__.py`); runners start with
  `python -m evals.run_retrieval_eval` (plan said `python evals/...py`, which cannot import
  `evals.matching`). Shared code in `evals/common.py`. Metrics hand-written in
  `evals/metrics.py`; percentiles use **nearest rank** (always a real measured value, no
  interpolation). Latency and abstention runs switch off the openai library's silent
  retries (`with_options(max_retries=0)`) and retry 429s themselves, so retries are
  counted and their waiting time is in `wall_ms`. Result files carry `git_commit`, with
  `+dirty` when uncommitted code produced them.
- **Retrieval eval fetches 10** chunks to report @1/@3/@5; `ask()` still gives the LLM 4.
- **Alternatives:** `numpy.percentile` (interpolates: can report a latency no request had);
  `sys.path` hacks in each script (fragile); library retries (hide the slow tail).

### D-034 Mini API with FastAPI (step 1e, 2026-10-14)
- **What:** `src/docpilot/api.py`: `POST /ask` (Pydantic request: 1 to 2000 characters;
  response: answer + sources without chunk text), clients opened once in `lifespan`, plain
  `def` endpoint (thread pool). `fastapi==0.143.1`, `uvicorn==0.54.0` (runtime),
  `httpx==0.28.1` (dev, for `TestClient`; already installed as an openai dependency).
  All MIT/BSD. FastAPI 0.143 also pulls `starlette 1.8.0` and `opentelemetry-api 1.45.1`
  (a small tracing interface, inactive unless configured).
- **Why:** FastAPI gives validation (422 before our code runs) and `/docs` for free; it is
  the Phase 7 framework anyway (PROJECT_DOCUMENTATION 15.1).
- **Alternatives:** Flask (no built-in validation or OpenAPI docs); Django (too large for
  one endpoint); `uvicorn[standard]` (extra speed-ups not needed on one laptop).
- **Tests:** `tests/test_api.py` replaces `ask` with a fake: no model, no key, no Qdrant.

### D-035 CI and repository settings (step 1f, 2026-10-14)
- **What:** `.github/workflows/ci.yml` job `test`: checkout v7.0.1, setup-python v7.0.0
  (pip cache), CPU-only `torch==2.14.1` from download.pytorch.org (the default Linux wheel
  pulls GPU libraries of several GB), then ruff, pytest, `scripts/check_file_lengths.py`.
  `.github/pull_request_template.md` with an "Eval impact" section.
- **Fixes found while preparing CI:** ruff 0.16 formats Python inside Markdown, and the
  plan sketches in `docs/` failed `ruff format --check .` -> `extend-exclude = ["docs"]`;
  a result JSON reached 744 lines -> `evals/common.to_json` writes one line per question
  (data unchanged, checked by re-loading); Pyrefly (VS Code) could not resolve `evals` ->
  `[tool.pyrefly] search-path = [".", "src"]` (pyrefly.org, 2026-10-14).
- **Public repo:** `GET /branches/main/protection` on the private repo returned 403
  "Upgrade to GitHub Pro or make this repository public" (2026-10-14). Pro is paid, so
  the plan's choice stands: public. History scan before that: 21 commits, no key-like
  strings, no `.env`, no downloaded docs or database files ever committed.
- **Learner's decision (2026-10-14):** the repo stays **private until the whole project is
  finished**, then goes public (the author email being visible is fine: proof of work).
  Consequence: no branch protection until then; CI still runs on every PR, and the PR
  workflow is followed by discipline. The Phase 1 gate item "direct push to `main`
  rejected" is deferred to the end of the project (plan deviation, recorded here).

### D-036 MLflow for experiment tracking (step 2.0, 2026-10-15)
- **What:** `mlflow==3.17.1` in `requirements-dev.txt` (not runtime). Backend: SQLite file
  `mlflow.db`; artifacts: `mlartifacts/` (both gitignored, `config.MLFLOW_TRACKING_URI`).
  `evals/tracking.py` logs one run per saved result file (params = settings, metrics =
  scores, tags = config id, commit, split, results file, ablation; the JSON attached), in
  one experiment per kind (`docpilot-retrieval`, `-latency`, `-abstention`). All three
  runners log automatically; `python -m evals.relog_results_to_mlflow` copies existing
  JSON files (never retyped; already-logged files skipped).
- **Why full, not `mlflow-skinny`:** skinny has "no SQL storage, server, UI" (PyPI page,
  2026-10-15); we need the UI and SQLite. Cost: 60 extra packages (Flask, pandas,
  SQLAlchemy, matplotlib, ...), and `protobuf` moved 7.36.2 -> 6.33.6; `pip check` clean,
  full suite 66 passed. MLflow emits a SQLAlchemy deprecation warning (its code, not ours).
- **Alternatives:** Weights & Biases (hosted, plan limits, data leaves the laptop);
  TensorBoard (training curves, not config comparison); JSON only (no search/compare UI).
- **Plan fix:** the re-log script lives in `evals/` (run with `python -m`), not `scripts/`,
  because it imports the `evals` package.

### D-037 PDF and Word (DOCX) support (learner request, 2026-10-15)
- **What:** step 2.7 widens from "PDF/HTML" to **PDF, Word (DOCX) and HTML** through Docling
  (one converter, Markdown output, then the same `blocks.py` pipeline). Golden questions
  are added for each new format.
- **Why:** the learner considers PDF and Word essential: learning material and own notes
  often come as PDF or DOCX. Docling lists PDF and DOCX as supported inputs (docs page,
  2026-10-15); current version 2.139.0 (verify API, CPU speed and install size at 2.7).
- **Scope kept (D-030):** these are **corpus files** added by the owner, not uploads from
  any user. User uploads stay stretch 8.6, after the Phase 6 guardrails gate.
- **Alternatives:** PyMuPDF (fast, weaker tables, PDF only) + python-docx (Word only): two
  libraries and two code paths instead of one; decided again at 2.7 with measurements.

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
| qdrant-client | 1.19.1 | 2026-10-12 | D-027; Apache-2.0; pulls pydantic 2.14.1, grpcio, pywin32 (Windows) |
| openai | 3.29.0 | 2026-10-12 | D-028; Apache-2.0; client library only |
| python-dotenv | 1.2.4 | 2026-10-09 | D-026; BSD-3-Clause, requires Python >=3.10 |
| fastapi | 0.143.1 | 2026-10-14 | D-034; MIT; pulls starlette 1.8.0, opentelemetry-api 1.45.1 |
| uvicorn | 0.54.0 | 2026-10-14 | D-034; BSD-3-Clause |
| httpx | 0.28.1 | 2026-10-14 | D-034; dev only (TestClient) |
| mlflow | 3.17.1 | 2026-10-15 | D-036; Apache-2.0; dev only; pulls 60 packages |
| pytest | 9.1.1 | 2026-10-03 | dev only |
| ruff | 0.16.10 | 2026-10-03 | dev only |

## Free-tier checks (filled when verified)

| Service | What was checked | Result | Verified on |
|---|---|---|---|
| Groq | models, rate limits | models seen by the account: gpt-oss-120b/20b (production), qwen3.8-27b (preview), no Llama 3.x; free-plan limits n/a (docs show Developer table) | 2026-10-12 |
| Gemini | free limits, data-use terms | n/a | n/a |
| OpenRouter | current free models | n/a | n/a |
| Oracle Cloud | Always Free allowance, region | n/a | n/a |
| AWS free plan | credits, duration, end of plan, card, instance types | USD 100 + up to 100 credits; 6 months or credits used; suspension, deletion after 90 days; card not required for most; t3/t4g micro+small, c7i-flex.large, m7i-flex.large | 2026-10-08 |
| AWS public IPv4 | hourly charge | USD 0.005 per IP-hour | 2026-10-08 |
| AWS EKS | control plane price | USD 0.10 per cluster-hour, no free tier | 2026-10-08 |
| MinIO community | still distributed? | archived Apr 2026; images and binaries removed Sep 2026 | 2026-10-08 |
| k3s | server node RAM | 2 GB minimum (docs) | 2026-10-08 |
| Terraform / OpenTofu | licence | Terraform BSL 1.1; OpenTofu MPL 2.0 | 2026-10-08 |
| GitHub | branch protection on free plan | private repo: 403 'Upgrade to GitHub Pro or make this repository public' (API); public: available. Actions minutes: n/a | 2026-10-14 |

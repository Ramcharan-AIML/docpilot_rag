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
| D-002 | Embeddings: `bge-small-en-v1.5` | accepted (revisit Phase 3) | 2026-10-03 | 2026-10-07 (model card) | n/a |
| D-003 | Vector DB: Qdrant, local mode then Docker | accepted | 2026-10-03 | not yet | n/a |
| D-004 | OpenAI-compatible LLM client; Groq default, Ollama fallback | accepted | 2026-10-03 | not yet | n/a |
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
| python-dotenv | 1.2.4 | 2026-10-09 | D-026; BSD-3-Clause, requires Python >=3.10 |
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
| AWS free plan | credits, duration, end of plan, card, instance types | USD 100 + up to 100 credits; 6 months or credits used; suspension, deletion after 90 days; card not required for most; t3/t4g micro+small, c7i-flex.large, m7i-flex.large | 2026-10-08 |
| AWS public IPv4 | hourly charge | USD 0.005 per IP-hour | 2026-10-08 |
| AWS EKS | control plane price | USD 0.10 per cluster-hour, no free tier | 2026-10-08 |
| MinIO community | still distributed? | archived Apr 2026; images and binaries removed Sep 2026 | 2026-10-08 |
| k3s | server node RAM | 2 GB minimum (docs) | 2026-10-08 |
| Terraform / OpenTofu | licence | Terraform BSL 1.1; OpenTofu MPL 2.0 | 2026-10-08 |
| GitHub | branch protection on free plan; Actions minutes | n/a (verify in Phase 1 step 1f) | n/a |

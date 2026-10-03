Continues from [phase_7_production.md](phase_7_production.md)

# Phase 7: Production (Implementation Plan, Part 2 of 2)

Part 2 covers **shipping**: 7.7 to 7.12.

---

## Step 7.7: Dockerfile and full Compose stack

### 7.7.1 `Dockerfile` (multi-stage)

```dockerfile
# ---------- stage 1: build wheels (has compilers; thrown away afterwards) ----------
# VERIFY: pin an exact patch tag and check arm64. Same minor version as dev (D-015).
FROM python:3.13-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ---------- stage 2: runtime (small, no compilers) ----------
FROM python:3.13-slim
# a normal user: if someone breaks into the app, they are not root in the container
RUN useradd --create-home --uid 1000 app
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY src/ src/
COPY pyproject.toml .
RUN pip install --no-cache-dir --no-deps -e .

# Bake model files into the image so containers never download at start-up
ENV HF_HOME=/app/hf_cache
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('BAAI/bge-small-en-v1.5'); CrossEncoder('BAAI/bge-reranker-base')"

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; \
urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "docpilot.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

Teaching points: layer order (requirements before source, so code changes do not
reinstall packages), multi-stage (smaller image, no build tools in production), non-root
user, baked models, health check.

CPU-only torch: the default torch wheel may pull large GPU libraries on x86. VERIFY the
CPU-only install method for torch and record the image size before and after.

**`.dockerignore`**: `.git`, `.venv`, `data/`, `qdrant_storage/`, `.env`, `evals/results/`,
`__pycache__`. Smaller build context, no secrets in the image.

### 7.7.2 `docker-compose.yml` (full)

| Service | Image | Notes |
|---|---|---|
| `api` | `ghcr.io/<user>/docpilot:<git-sha>` | env from `.env`; depends on qdrant, redis, postgres (healthy) |
| `qdrant` | pinned tag | volume `qdrant_storage` |
| `redis` | pinned tag | `maxmemory` + eviction policy set; no public port |
| `postgres` | pinned tag | volume `pg_data`; password from `.env` |
| `prometheus` | pinned tag | `deploy/prometheus.yml` mounted |
| `grafana` | pinned tag | provisioning mounted; admin password from `.env` |
| `caddy` | pinned tag | only service with public ports 80/443; `deploy/Caddyfile` |
| tracing | per D-009 | |
| `ollama` (optional) | pinned tag | profile `local-llm` so it only starts when asked |

Every service: `restart: unless-stopped`, a `healthcheck`, memory limits sized to the VM.

**`deploy/Caddyfile`**

```text
docpilot.duckdns.org {            # your DuckDNS name
    reverse_proxy api:8000         # Caddy gets and renews the HTTPS certificate itself
}
grafana.docpilot.duckdns.org {
    reverse_proxy grafana:3000
}
```

**Done when:** `docker compose up -d` on the laptop brings everything up; `/ready` is green;
Grafana shows the `api` target as UP in Prometheus.

---

## Step 7.8: GitHub Actions CI/CD

### 7.8.1 `.github/workflows/ci.yml` (every pull request and push)

```yaml
# VERIFY: current action versions (checkout, setup-python, docker actions)
name: ci
on: [pull_request, push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@vX
      - uses: actions/setup-python@vX
        with: {python-version: "3.13"}
      - run: pip install -r requirements-dev.txt && pip install -e .
      - run: ruff check . && ruff format --check .
      - run: pytest -q
      - run: python scripts/check_file_lengths.py          # Rule 1: max 500 lines
      - run: pip-audit -r requirements.txt                 # known-vulnerable packages
  eval-gate:
    needs: test
    runs-on: ubuntu-latest
    services:
      qdrant: {image: "qdrant/qdrant:vX.Y.Z", ports: ["6333:6333"]}
    steps:
      # ... checkout, install
      - run: python scripts/02_ingest.py --fixture-corpus   # small committed test corpus
      - run: python evals/run_retrieval_eval.py --split dev --config-id ci
      - run: python evals/check_gate.py --baseline evals/baseline.json --tolerance 0.02
```

**The eval gate in plain words:** CI indexes a small corpus that we are allowed to commit
(our own fixture pages, or doc pages whose license allows it; VERIFY), runs the
deterministic retrieval eval, and `check_gate.py` exits with an error if Recall@5 or MRR
is below `baseline - tolerance`. No LLM tokens are used (D-011).

**Prove it works:** open a pull request that deliberately breaks retrieval (for example
remove the BGE query prefix). The gate must fail. Screenshot it for the README. Then close
the PR.

### 7.8.2 `.github/workflows/eval.yml` (manual or nightly)

Full generation evals with the judge LLM; keys from GitHub Secrets; results uploaded as
an artifact. Not a merge blocker (tokens are scarce and judges are noisy).

### 7.8.3 `.github/workflows/deploy.yml` (on push to `main` after CI passes)

1. Build the image for `linux/arm64` with Docker Buildx (QEMU emulation; VERIFY build time
   on free runners, or check for native ARM runners for public repos).
2. Push to GitHub Container Registry tagged with the git SHA.
3. SSH to the VM (key in GitHub Secrets), `docker compose pull && docker compose up -d`.
4. Smoke test: `curl https://<domain>/ready`; fail the job if not 200.

Rollback: re-deploy the previous SHA tag. Write the one-line command in the README.

Also: enable Dependabot (or rely on `pip-audit`) and GitHub secret scanning.

---

## Step 7.9: Deploy to the free VM

1. VERIFY Oracle Cloud Always Free: current ARM allowance, region capacity, sign-up
   requirements. Record the date. If sign-up fails, use the fallback (step 4).
2. Create the VM (Ubuntu, ARM). Open ports 80 and 443 in **both** the cloud security list
   and the VM firewall (a classic "it does not work" cause on Oracle).
3. Install Docker; create the `app` deploy user; add the GitHub deploy SSH key.
4. **Fallback:** run Compose on the laptop and publish with a Cloudflare Tunnel (VERIFY
   current free terms). The architecture does not change, only the host.
5. DuckDNS: point a free subdomain to the VM IP. Caddy fetches certificates automatically.
6. Copy `.env` to the VM by hand (`scp`); it never goes through git.
7. Ingest the corpus on the VM (or copy the Qdrant snapshot from the laptop: VERIFY the
   snapshot API).
8. Demo UI: a small Gradio or Streamlit page (`ui/app.py`) calling the public API with a
   demo key, hosted on a Hugging Face Space (VERIFY free CPU limits and sleep behaviour).
   The demo key has a strict rate limit.

**Security checklist** (from `PROJECT_DOCUMENTATION.md` 15.8): no secrets in git, `.env`
ignored, non-root containers, CORS limited to the UI origin, input size limits, rate
limiting, dependency scanning, least-privilege tools, PII-free logs, only Caddy exposed,
Grafana behind a password, SSH by key only.

---

## Step 7.10: Load testing

**File:** `loadtest/locustfile.py` (Locust, VERIFY version; k6 is the alternative)

Scenarios:
1. Steady users asking cached questions (measures the cache path).
2. Steady users asking new questions (measures the full path; watch free-tier limits:
   keep the user count low and point at Ollama or a mock LLM if needed).
3. A burst above the rate limit: expect `429`s, not errors.
4. Provider failure: bad key for the first provider: expect fallbacks, no `5xx`.

Report p50/p95 latency, error rate, 429 rate, fallback count, with the VM size noted.

---

## Step 7.11: Incremental ingestion

**File:** `src/docpilot/ingestion/manifest.py`, manifest stored in Postgres (or a JSON
file in `data/processed/` for dev)

```text
for each document:
    new_hash = sha256(cleaned text)
    if new_hash == manifest[source]:  skip (nothing changed)
    else: delete this source's points (filter by source), re-chunk, re-embed, upsert,
          update manifest[source] = new_hash, version += 1
for each source in manifest but not on disk:  delete its points (document was removed)
```

**Test:** change one doc, re-run: only that doc's chunks change (count the upserts).
Also bump cache versions so stale cached answers are not served.

---

## Step 7.12: README, demo, and the big interview file

1. `README.md`: one-paragraph pitch, architecture diagram (from `docs/architecture/`),
   **the ablation table with real numbers**, the safety table, screenshot of the failing
   CI gate, Grafana screenshot, demo link, run-it-yourself instructions, honest
   limitations section.
2. Short demo video or GIF (free screen recorder).
3. Merge all `docs/interview/phase_*_interview.md` files into
   `docs/interview/ALL_INTERVIEW_QUESTIONS.md` (+ `2_`, `3_` parts by Rule 1), with real
   numbers filled in everywhere a `n/a` placeholder was.

---

## Phase 7 gate (and the project's definition of done)

- [ ] public HTTPS URL works; auth and rate limit on
- [ ] CI: lint, tests, 500-line check, pip-audit, retrieval eval gate; gate failure proven
- [ ] deploy workflow deploys on merge; rollback documented
- [ ] traces and Grafana show real traffic; D-009 closed
- [ ] semantic cache false-hit rate measured (or cache disabled with reason)
- [ ] load test report with real numbers
- [ ] HITL works with Postgres checkpointer across a container restart
- [ ] README complete; big interview file assembled
- [ ] every version pinned and verified; `git tag phase-7`
- [ ] everything in `PROJECT_DOCUMENTATION.md` section 23 checked

Continues from [phase_7_production.md](phase_7_production.md)

# Phase 7: Production (Implementation Plan, Part 2 of 4)

Part 2 covers **packaging and CI/CD**: 7.8 to 7.10.
Teaching: `teaching/2_phase_7_production.md`, `teaching/primer_git_workflow.md`,
`teaching/primer_aws.md` (sections on ECR and IAM/OIDC).

---

## Step 7.8: Dockerfile (multi-stage, multi-architecture)

### 7.8.1 `Dockerfile`

```dockerfile
# ---------- stage 1: build wheels (has compilers; thrown away afterwards) ----------
# VERIFY: pin an exact patch tag; confirm amd64 AND arm64 variants. Same minor as dev (D-015).
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
COPY pyproject.toml README.md ./
COPY src/ src/
# a normal (not editable) install: the image never changes after it is built
RUN pip install --no-cache-dir --no-deps .

# Bake model files into the image so containers never download at start-up
ENV HF_HOME=/app/hf_cache
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('BAAI/bge-small-en-v1.5', revision='5c38ec7c405ec4b44b94cc5a9bb96e735b38267a'); \
CrossEncoder('BAAI/bge-reranker-base')"

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; \
urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "docpilot.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

Teaching points: layer order (requirements before source, so code changes do not reinstall
packages), multi-stage (smaller image, no build tools), non-root user, baked and pinned
models, health check. Dockerfile comments must be on their **own** lines.

### 7.8.2 Things to check and record

| Check | Why |
|---|---|
| CPU-only torch (VERIFY the install method, e.g. the CPU wheel index) | the default Linux torch wheel can pull large GPU libraries; record image size before/after |
| A Linux lock file | `requirements-lock.txt` was generated on Windows; generate `requirements-lock-linux.txt` inside the build container (D-016 follow-up) |
| **Two architectures** | AWS `m7i-flex.large` = amd64; Oracle A1 = arm64. Build both with Docker Buildx (`--platform linux/amd64,linux/arm64`) |
| `.dockerignore` | `.git`, `.venv`, `data/`, `qdrant_storage/`, `seaweed_data/`, `.env`, `mlflow.db`, `mlartifacts/`, `evals/results/`, `infra/`, `__pycache__` |

**Done when:** `docker build` works locally; image size recorded; the container answers
`/health`; `docker buildx build --platform linux/arm64` also succeeds (emulated on your PC).

---

## Step 7.9: Full Docker Compose stack

`docker-compose.yml` (used for local development and as the first deployment on EC2):

| Service | Image | Notes |
|---|---|---|
| `api` | `<ecr-or-ghcr>/docpilot-api:<git-sha>` | env from `.env`; depends on qdrant, redis, postgres (healthy) |
| `qdrant` | pinned tag | volume `qdrant_storage` |
| `redis` | pinned tag | `maxmemory` + eviction policy; no public port |
| `postgres` | pinned tag | volume `pg_data`; password from `.env` |
| `prometheus` | pinned tag | `deploy/prometheus.yml`, alert rules mounted |
| `grafana` | pinned tag | provisioning + dashboards mounted; admin password from `.env` |
| `caddy` | pinned tag | only service with public ports 80/443; `deploy/Caddyfile` |
| tracing | per D-009 | Langfuse / Phoenix / MLflow tracing |
| `seaweedfs` (profile `local`) | pinned tag | local S3 only; on AWS the app uses real S3 |
| `mlflow` (profile `dev`) | pinned tag | experiments; not needed on the server |
| `ollama` (profile `local-llm`) | pinned tag | only when asked |

**Profiles** let one file serve laptop and server: `docker compose --profile local up -d`
on the laptop; plain `docker compose up -d` on EC2.
Every service: `restart: unless-stopped`, a `healthcheck`, a memory limit sized from
`docker stats` measurements (record them: they decide the EC2 size in 7.11).

**`deploy/Caddyfile`**

```text
# your DuckDNS name; Caddy gets and renews the HTTPS certificate itself
docpilot.duckdns.org {
    reverse_proxy api:8000
}
grafana.docpilot.duckdns.org {
    reverse_proxy grafana:3000
}
```

**Done when:** `docker compose --profile local up -d` brings everything up on the laptop;
`/ready` is green; Prometheus shows `api` as UP; total RAM use recorded.

---

## Step 7.10: GitHub Actions CI/CD into AWS

### 7.10.1 `ci.yml` (already exists from Phases 1-2; extend it)

| Job | Added in | Does |
|---|---|---|
| `test` | 1f | ruff, pytest, 500-line check |
| `eval-gate` | 2.10 | retrieval eval on the fixture corpus vs baseline |
| `audit` | 7.10 | `pip-audit -r requirements.txt` (known vulnerable packages) |
| `terraform-check` | 7.12 | `terraform fmt -check` and `terraform validate` on `infra/` (no cloud access needed) |

Branch protection on `main` requires all four.

### 7.10.2 `deploy.yml` (on push to `main`, after CI passes)

```yaml
# Sketch. VERIFY action names/versions (configure-aws-credentials, amazon-ecr-login,
# docker/setup-buildx-action, docker/build-push-action) on build day.
name: deploy
on:
  push:
    branches: [main]
permissions:
  id-token: write        # lets GitHub request a short-lived OIDC token for AWS
  contents: read
  packages: write        # push to GHCR as well
jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@vX
      - uses: aws-actions/configure-aws-credentials@vX
        with:
          role-to-assume: ${{ vars.AWS_DEPLOY_ROLE_ARN }}   # created by Terraform (7.12)
          aws-region: ${{ vars.AWS_REGION }}
      - uses: aws-actions/amazon-ecr-login@vX
      - uses: docker/setup-qemu-action@vX                     # emulation for arm64 builds
      - uses: docker/setup-buildx-action@vX
      - uses: docker/build-push-action@vX
        with:
          platforms: linux/amd64,linux/arm64
          push: true
          tags: |
            ${{ vars.ECR_REPO }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}/docpilot-api:${{ github.sha }}
      - name: Deploy through SSM (no SSH)
        run: |
          aws ssm send-command --instance-ids "${{ vars.EC2_INSTANCE_ID }}" \
            --document-name "AWS-RunShellScript" \
            --parameters commands="/opt/docpilot/deploy.sh ${{ github.sha }}"
      - name: Smoke test
        run: curl --fail https://${{ vars.PUBLIC_HOST }}/ready
```

**Why OIDC (no AWS keys in GitHub):** GitHub proves to AWS "I am a workflow of repo X on
branch main"; AWS hands back credentials that expire within the hour. Nothing long-lived to
leak. The trust rule (which repo, which branch) lives in Terraform (7.12).

**Why SSM instead of SSH:** no port 22 open, no SSH key to store in GitHub; every command is
logged in AWS.

**`/opt/docpilot/deploy.sh`** (installed by cloud-init, kept in `infra/bootstrap/`): pulls
the image tag, applies it (Compose in 7.13; `kubectl set image` once on k3s in 7.14), waits
for `/ready`, and rolls back to the previous tag if it never gets ready.

**Rollback by hand:** re-run `deploy.sh <previous-sha>` (or `kubectl rollout undo`).
Written in the README.

### 7.10.3 `eval.yml` (manual or nightly)

Full generation evals with the judge LLM; keys from GitHub **Secrets** (the only secrets
GitHub holds: free-tier LLM keys for the judge); results uploaded as an artifact and logged to
MLflow if a server is reachable. Not a merge blocker.

### 7.10.4 GitHub settings checklist

- Variables (not secrets): `AWS_REGION`, `AWS_DEPLOY_ROLE_ARN`, `ECR_REPO`,
  `EC2_INSTANCE_ID`, `PUBLIC_HOST`.
- Secrets: judge LLM keys only.
- Dependabot (or pip-audit only) and secret scanning on.
- `main` protected; PR template; tags pushed per phase.

**Done when (after 7.12 exists):** merging a PR to `main` builds both architectures, pushes to
ECR and GHCR, deploys through SSM, and the smoke test passes, with no AWS key stored anywhere.

Continued in [3_phase_7_production.md](3_phase_7_production.md)

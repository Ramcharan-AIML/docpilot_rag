# DocPilot server image (Phase 7 B2, D-064). Teaching: docs/production/03_teach_docker_images.md
# Build: docker build -t docpilot:dev .
# Run:   docker run --rm -p 8000:8000 --env-file .env -e QDRANT_URL=http://host.docker.internal:6333 docpilot:dev
#
# Two stages: Node builds the React files, then only those files go into the Python image
# (the final image has no Node). Slow, rarely-changing steps first; my code last (cache).

# ---------- Stage 1: build the React UI ----------
# Exact tags, never "latest" (checked on Docker Hub 2026-10-23; amd64 + arm64).
FROM node:22.23.4-bookworm-slim AS web
WORKDIR /web
# package files first: `npm ci` is re-run only when the dependencies change
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# ---------- Stage 2: the Python app ----------
FROM python:3.13.17-slim-bookworm AS app

# PYTHONDONTWRITEBYTECODE: no .pyc clutter. PYTHONUNBUFFERED: logs appear at once.
# PYTHONPATH: run the code from /app/src, so config.PROJECT_ROOT = /app (like the laptop).
# HF_HOME: where Hugging Face models are stored (baked in below).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src \
    HF_HOME=/app/.cache/huggingface
WORKDIR /app

# 1) CPU-only torch (no GPU on the server; the default wheel pulls GBs of CUDA).
#    Same version as the laptop's lock; wheels for x86_64 and aarch64 checked 2026-10-23.
RUN pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu

# 2) The app's packages, every sub-package pinned to the laptop's tested versions.
COPY requirements-server.txt requirements-lock.txt ./
RUN pip install -r requirements-server.txt -c requirements-lock.txt

# 3) A non-root user: a break-in through the app gets fewer powers.
RUN useradd --create-home --uid 1000 docpilot \
    && mkdir -p /app/data /app/.cache \
    && chown -R docpilot:docpilot /app
USER docpilot

# 4) My code and the built UI (change often: last, so the layers above stay cached).
COPY --chown=docpilot:docpilot src/ ./src/
COPY --from=web --chown=docpilot:docpilot /web/dist ./web/dist

# 5) Bake the 3 models in (BGE embedder, BM25, MiniLM reranker; pinned revisions in
#    config.py) by running the same warm-up the server runs at start.
RUN python -c "from docpilot.retrieval.pipeline import warm_up_models; warm_up_models()" \
    && ln -s "$(ls -d /app/.cache/fastembed/models--Qdrant--bm25/snapshots/*)" /app/.cache/bm25
# From here on: never download. A missing model fails loudly instead of slowly.
# BM25_MODEL_PATH: fastembed's offline check wants 2 files its repo lacks, so we point it
# at the downloaded word lists directly (found with `docker run --network none`, D-064).
ENV HF_HUB_OFFLINE=1 \
    BM25_MODEL_PATH=/app/.cache/bm25

EXPOSE 8000
# Docker marks the container "unhealthy" if /health stops answering. The slim image has no
# curl, so Python does the request. start-period: model loading takes a while.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

# 0.0.0.0 = listen on all of the container's network cards (127.0.0.1 would be unreachable
# from outside the container). Behind Caddy, set FORWARDED_ALLOW_IPS so the real visitor IP
# is used for the A2 limits (uvicorn reads that variable; see docker-compose.prod.yml).
CMD ["uvicorn", "docpilot.api:app", "--host", "0.0.0.0", "--port", "8000"]

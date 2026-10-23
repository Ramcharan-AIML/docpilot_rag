"""All DocPilot settings in one place. Secrets come from .env, never from this file.

An experiment should change one line here, not hunt through five files (D-005).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# src/docpilot/config.py -> parents[0] is docpilot/, [1] is src/, [2] is the project root.
# This works because of the editable install (D-013): the code runs from the repo folder.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Copy the lines of .env into os.environ. A variable that is already set (CI, Docker)
# is NOT overwritten, so the real environment always wins over the file (D-026).
load_dotenv(PROJECT_ROOT / ".env")

# --- paths ---
# DOCS_DIR, QDRANT_PATH and MANIFEST_DIR can be moved with environment variables: the CI
# eval gate (step 2.10) points them at the fixture corpus and a temporary folder, so it runs
# the real ingest and eval code without touching the laptop's index.
DOCS_DIR = Path(os.getenv("DOCPILOT_DOCS_DIR", PROJECT_ROOT / "data" / "docs"))
# Code files the docs include with {* ... *} markers (step 2.3), one folder per technology:
# data/code/fastapi/docs_src/... Kept apart from DOCS_DIR so the loader never reads them.
CODE_DIR = Path(os.getenv("DOCPILOT_CODE_DIR", PROJECT_ROOT / "data" / "code"))
# Qdrant server in Docker (step 3.1, docker-compose.yml): set QDRANT_URL=http://127.0.0.1:6333
# in .env (127.0.0.1, not localhost: see .env.example). Empty (the default) = local mode in
# QDRANT_PATH: the tests and CI use that, because there is no Docker there. (The plan's
# default URL would have broken CI.)
QDRANT_URL = os.getenv("QDRANT_URL", "")
# local-mode Qdrant saves its files here (gitignored)
QDRANT_PATH = Path(os.getenv("DOCPILOT_QDRANT_PATH", PROJECT_ROOT / "qdrant_local"))
# How each collection was built (strategy, size, clean, includes), one JSON per collection,
# so an eval records the real settings of the index it tested (gitignored, rebuilt by ingest).
MANIFEST_DIR = Path(
    os.getenv("DOCPILOT_MANIFEST_DIR", PROJECT_ROOT / "data" / "processed" / "collections")
)
# PDF/DOCX converted to Markdown by Docling (step 2.7), cached: about 3 s per PDF page on CPU.
CONVERTED_DIR = PROJECT_ROOT / "data" / "processed" / "converted"

# --- embeddings (D-002, model card checked 2026-10-07) ---
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
# Model files are dependencies too: pin the exact commit, same as Labs 1 and 2.
EMBEDDING_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
EMBEDDING_DIM = 384
# BGE v1.5 was trained with this instruction on the QUESTION side only; chunks get no prefix.
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# --- chunking (D-006: a weak baseline on purpose) ---
CHUNK_SIZE = 800  # characters, not tokens
CHUNK_OVERLAP = 100
CHUNK_STRATEGY = "fixed"  # Phase 2 adds recursive, semantic, ... (one name per strategy)
# Phase 2 chunkers measure size in model tokens (D-038; the model reads at most 510).
# 50 of 400 = 12.5% overlap, the same share as C0's 100 of 800 characters.
CHUNK_TOKENS = 400
CHUNK_OVERLAP_TOKENS = 50
# Parent-child (C3): small children are searched, their parent section goes to the LLM.
# Parents are not embedded, so they may pass 510; the cap keeps 4 parents in the prompt
# small enough for Groq's free 8000 tokens per minute (checked 2026-10-19, D-041).
CHILD_TOKENS = 128
PARENT_TOKENS = 800
# Semantic (C2): a new chunk starts where neighbour similarity is in the lowest N percent.
# Dry run 2026-10-19 (4 pages, size 400): 25 -> 119 chunks, median 44 tokens (too small);
# 5 -> 50, median 320 (mostly cut by the size cap); 10 -> 64, median 174, the same size as
# hierarchical (65, median 174), so C2 vs C4 compares WHERE we cut, not how big (D-041).
SEMANTIC_PERCENTILE = 10
# Contextual (C5): change the version whenever the prompt changes (it is the cache key).
CONTEXT_PROMPT_VERSION = "ctx-v1"
CONTEXT_CACHE = PROJECT_ROOT / "data" / "processed" / "context_cache.jsonl"

# --- retrieval ---
TOP_K = 4
# Rerankers (step 3.5, D-055): a cross-encoder reads question + chunk together. Short name
# -> (model, pinned revision). Model cards checked on Hugging Face 2026-10-22; both read at
# most 512 tokens. bge-base: MIT, 1.1 GB. minilm: Apache-2.0, 91 MB, trained on MS MARCO.
RERANKERS = {
    "bge-base": ("BAAI/bge-reranker-base", "2cfc18c9415c912f9d8155881c133215df768a70"),
    "minilm": ("cross-encoder/ms-marco-MiniLM-L6-v2", "233902d25c440f23af6f7d6e94d2946bac0bee0a"),
}
RERANKER = "minilm"  # D-055: as good as bge-base on dev, 13x faster on this CPU
RERANKER_MAX_TOKENS = 512
# The collection the app, 03_ask.py and the evals use by default. Since D-047 (step 2.9):
# FT-200 = fixed 200 tokens, overlap 25, cleaned, includes resolved. Build it with
#   python scripts/02_ingest.py --clean --includes --strategy fixed_tokens --size 200
#       --overlap 25 --collection docpilot_v1_ft200
# (C0 = "docpilot_naive" / "docpilot_v1_c0" stays as the baseline row, not the app.)
COLLECTION_NAME = "docpilot_v1_ft200"
# The app's ingest recipe in one place; the CI eval gate builds its index with it too, so
# the gate always tests the chunking the app really uses.
INGEST_ARGS = ["--clean", "--includes", "--strategy", "fixed_tokens", "--size", "200"]
INGEST_ARGS += ["--overlap", "25"]
INGEST_COMMAND = (
    f"python scripts/02_ingest.py {' '.join(INGEST_ARGS)} --collection {COLLECTION_NAME}"
)

# --- object storage (step 3.1b, D-019, D-051) ---
# Laptop: SeaweedFS in Docker; .env sets S3_ENDPOINT_URL=http://127.0.0.1:8333 and the two
# local keys. AWS (Phase 7): leave all three EMPTY, so boto3 talks to real Amazon S3 with the
# machine's IAM role and no keys in any file. Same code, one setting.
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
# The object store's address as seen from INSIDE Docker: Qdrant downloads snapshots from it
# by itself. Laptop: http://seaweedfs:8333 (the Compose service name). AWS: empty.
S3_ENDPOINT_URL_DOCKER = os.getenv("S3_ENDPOINT_URL_DOCKER", "")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")  # the real region is chosen in Phase 7
# Bucket names must be unique across ALL of AWS, so Phase 7 sets its own through .env.
RAW_DOCS_BUCKET = os.getenv("RAW_DOCS_BUCKET", "docpilot-raw-docs")
SNAPSHOT_BUCKET = os.getenv("SNAPSHOT_BUCKET", "docpilot-snapshots")
MLFLOW_BUCKET = os.getenv("MLFLOW_BUCKET", "docpilot-mlflow")  # used by the MLflow server

# --- LLM (D-004) ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
# No default model: free model names change often. Check the provider's docs, set it in .env.
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_TIMEOUT_SECONDS = 30

# The exact sentence the model must say when the documents do not contain the answer.
# Evals search for this text to count abstentions, so it lives in one place.
NOT_FOUND_PHRASE = "I could not find this in the documents."
# Phase 6 (D-059): what a blocked request gets. It never says WHICH rule fired:
# attackers learn from details. The reason is logged on the server instead.
BLOCKED_PHRASE = "Sorry, I can't help with that. Please ask a question about the documentation."

# --- experiment tracking (D-022, D-036): local MLflow "lab notebook", gitignored ---
MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI", f"sqlite:///{PROJECT_ROOT.as_posix()}/mlflow.db"
)
MLFLOW_ARTIFACT_DIR = PROJECT_ROOT / "mlartifacts"  # attached result files live here

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
DOCS_DIR = PROJECT_ROOT / "data" / "docs"
# Code files the docs include with {* ... *} markers (step 2.3), one folder per technology:
# data/code/fastapi/docs_src/... Kept apart from DOCS_DIR so the loader never reads them.
CODE_DIR = PROJECT_ROOT / "data" / "code"
QDRANT_PATH = PROJECT_ROOT / "qdrant_local"  # local-mode Qdrant saves its files here (gitignored)
# How each collection was built (strategy, size, clean, includes), one JSON per collection,
# so an eval records the real settings of the index it tested (gitignored, rebuilt by ingest).
MANIFEST_DIR = PROJECT_ROOT / "data" / "processed" / "collections"

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
COLLECTION_NAME = "docpilot_naive"

# --- LLM (D-004) ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
# No default model: free model names change often. Check the provider's docs, set it in .env.
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_TIMEOUT_SECONDS = 30

# The exact sentence the model must say when the documents do not contain the answer.
# Evals search for this text to count abstentions, so it lives in one place.
NOT_FOUND_PHRASE = "I could not find this in the documents."

# --- experiment tracking (D-022, D-036): local MLflow "lab notebook", gitignored ---
MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI", f"sqlite:///{PROJECT_ROOT.as_posix()}/mlflow.db"
)
MLFLOW_ARTIFACT_DIR = PROJECT_ROOT / "mlartifacts"  # attached result files live here

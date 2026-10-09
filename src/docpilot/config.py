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
QDRANT_PATH = PROJECT_ROOT / "qdrant_local"  # local-mode Qdrant saves its files here (gitignored)

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

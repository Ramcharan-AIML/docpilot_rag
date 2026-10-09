# Phase 1: Naive Baseline, Eval Harness, Mini API (Part 1 of 2)

**Goal of the phase:** build the simplest RAG that works end to end, measure it honestly
(C0), and put it behind one API endpoint. C0 is the number every later phase must beat.

**Teaching companion:** `docs/teaching/phase_1_baseline.md`
**Part 2:** `2_phase_1_baseline.md` (steps 1b to 1e and the gate)

```text
Phase 1 data flow

01_download_docs.py ─▶ data/docs/fastapi/*.md
02_ingest.py:   loader ─▶ chunker ─▶ embedder ─▶ vector_store (collection docpilot_naive)
03_ask.py:      question ─▶ embed_query ─▶ search top 4 ─▶ prompt ─▶ LLM ─▶ answer + sources
```

Settings (from `PROJECT_DOCUMENTATION.md` section 18.1): model `BAAI/bge-small-en-v1.5`
(384 dims), chunk size 800 characters, overlap 100, top-k 4, cosine distance, collection
`docpilot_naive`.

New dependencies (decision log entry + pinned versions first): `qdrant-client`, `openai`
(the client library only; we point it at free providers), `python-dotenv`.

---

## Step 1a.1: `src/docpilot/config.py`

**Goal:** one place for every setting, so an experiment changes one line.

```python
"""All DocPilot settings in one place. Secrets come from .env, never from this file."""
import os
from pathlib import Path

from dotenv import load_dotenv

# src/docpilot/config.py -> parents[2] is the project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# --- paths ---
DOCS_DIR = PROJECT_ROOT / "data" / "docs"
QDRANT_PATH = PROJECT_ROOT / "qdrant_local"   # local-mode Qdrant stores files here

# --- embeddings (decision D-002) ---
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
# Fixed 2026-10-09: the plan forgot the pinned revision the labs use (D-002, D-026).
EMBEDDING_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
EMBEDDING_DIM = 384
# BGE v1.5 was trained with this instruction on the QUESTION side only.
# VERIFY: exact text on the model card on build day.
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# --- chunking (decision D-006: weak baseline on purpose) ---
CHUNK_SIZE = 800        # characters, not tokens
CHUNK_OVERLAP = 100

# --- retrieval ---
TOP_K = 4
COLLECTION_NAME = "docpilot_naive"

# --- LLM (decision D-004) ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
LLM_MODEL = os.getenv("LLM_MODEL", "")        # VERIFY current free model name; set in .env
LLM_TIMEOUT_SECONDS = 30

NOT_FOUND_PHRASE = "I could not find this in the documents."
```

**Done when:** `python -c "from docpilot import config; print(config.DOCS_DIR)"` prints a
real path.

---

## Step 1a.2: `src/docpilot/loader.py`

**Goal:** turn files on disk into simple `Document` objects.

```python
"""Read .md and .txt files into Document objects."""
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_SUFFIXES = {".md", ".txt"}


@dataclass
class Document:
    text: str
    source: str  # path relative to the docs folder, e.g. "fastapi/query-params.md"


def load_documents(folder: Path) -> list[Document]:
    """Load every supported file under `folder`, in a stable (sorted) order."""
    documents: list[Document] = []
    for path in sorted(folder.rglob("*")):
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        # as_posix() gives forward slashes on Windows too, so sources look the same everywhere
        source = path.relative_to(folder).as_posix()
        documents.append(Document(text=text, source=source))
    return documents
```

Why sorted: the same input must give the same chunks in the same order every run, or eval
numbers drift for no reason.

**Test:** `tests/test_loader.py` writes two small files into pytest's `tmp_path` and checks
both come back with the right `source`, and that a `.png` file is ignored.

---

## Step 1a.3: `src/docpilot/chunker.py` + `tests/test_chunker.py`

**Goal:** fixed-size chunks with overlap. Deliberately naive (D-006).

```python
"""Fixed-size chunking: cut every N characters, neighbours share some text."""
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source: str
    chunk_number: int  # 0, 1, 2 ... inside one source; used in citations


def fixed_size_chunks(text: str, source: str, chunk_size: int = 800,
                      overlap: int = 100) -> list[Chunk]:
    """Split text into pieces of `chunk_size` characters.

    Each piece starts `chunk_size - overlap` characters after the previous one, so a
    sentence cut at the end of one chunk appears whole at the start of the next.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        # overlap >= chunk_size would never move forward: an infinite loop
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    step = chunk_size - overlap
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        piece = text[start:start + chunk_size]
        if piece.strip():  # skip pieces that are only whitespace
            chunks.append(Chunk(text=piece, source=source, chunk_number=len(chunks)))
        if start + chunk_size >= len(text):
            break  # this piece already reached the end
        start += step
    return chunks
```

**Tests (`tests/test_chunker.py`)**, each one a small function:

1. empty text gives an empty list
2. text shorter than `chunk_size` gives exactly one chunk
3. the last `overlap` characters of chunk 0 equal the first `overlap` characters of chunk 1
4. `overlap >= chunk_size` raises `ValueError`
5. chunk numbers are 0, 1, 2 ... with no gaps

**Run:** `pytest tests/test_chunker.py -q`

---

## Step 1a.4: `src/docpilot/embedder.py`

**Goal:** load the model once; embed chunks and questions (questions get the prefix).

```python
"""Turn text into vectors with a local sentence-transformers model."""
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from docpilot import config


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Load the model the first time it is needed, then reuse it (loading takes seconds)."""
    return SentenceTransformer(config.EMBEDDING_MODEL)


def embed_documents(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Embed chunks for storage. No query prefix here: documents are not questions."""
    vectors = get_model().encode(
        texts,
        batch_size=batch_size,          # 32 at a time keeps memory use steady on CPU
        normalize_embeddings=True,      # length 1, so dot product == cosine similarity
        show_progress_bar=True,
    )
    return vectors.tolist()


def embed_query(question: str) -> list[float]:
    """Embed one question for search, with the BGE instruction prefix."""
    vector = get_model().encode(config.BGE_QUERY_PREFIX + question, normalize_embeddings=True)
    return vector.tolist()
```

Why `lru_cache` instead of a global variable: same effect (load once), but no mutable global
and easy to reset in tests with `get_model.cache_clear()`.

---

## Step 1a.5: `src/docpilot/vector_store.py`

**Goal:** the only file that talks to Qdrant. Swapping databases later means changing this
file only.

```python
"""Qdrant helpers: create a collection, add chunks, search."""
import uuid
from pathlib import Path

from qdrant_client import QdrantClient, models   # VERIFY: API on installed version

from docpilot.chunker import Chunk


def get_client(path: Path) -> QdrantClient:
    """Local mode: Qdrant runs inside this Python process and saves to a folder.
    Only ONE process can open the folder at a time (D-003; fixed by Docker in Phase 3)."""
    return QdrantClient(path=str(path))


def create_fresh_collection(client: QdrantClient, name: str, dimension: int) -> None:
    """Delete the collection if it exists, then create it empty. Makes re-runs repeatable."""
    if client.collection_exists(name):
        client.delete_collection(name)
    client.create_collection(
        collection_name=name,
        vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE),
    )


def make_point_id(chunk: Chunk) -> str:
    """Same chunk -> same id on every run (uuid5 is a hash, not random)."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{chunk.source}#{chunk.chunk_number}"))


def add_chunks(client: QdrantClient, name: str, chunks: list[Chunk],
               vectors: list[list[float]]) -> None:
    points = []
    for chunk, vector in zip(chunks, vectors, strict=True):  # strict: lengths must match
        payload = {"text": chunk.text, "source": chunk.source,
                   "chunk_number": chunk.chunk_number}
        points.append(models.PointStruct(id=make_point_id(chunk), vector=vector,
                                         payload=payload))
    client.upsert(collection_name=name, points=points)


def search(client: QdrantClient, name: str, query_vector: list[float],
           top_k: int) -> list[dict]:
    """Return the top_k closest chunks as plain dicts (text, source, chunk_number, score)."""
    response = client.query_points(collection_name=name, query=query_vector,
                                   limit=top_k, with_payload=True)
    hits = []
    for point in response.points:
        hit = dict(point.payload)
        hit["score"] = point.score
        hits.append(hit)
    return hits
```

---

## Step 1a.6: `src/docpilot/llm.py`

**Goal:** one client that works for Groq, OpenRouter, Ollama (and Gemini's
OpenAI-compatible endpoint). The provider is a setting, not code.

```python
"""One OpenAI-compatible chat client for several free providers (decision D-004)."""
import os

from openai import OpenAI   # the library only; no OpenAI account is used

from docpilot import config

# provider -> (base URL, name of the env var holding the key)
# VERIFY: every URL on the provider's docs on build day.
PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "ollama": (os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"), None),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY"),
}


def get_llm_client(provider: str = config.LLM_PROVIDER) -> OpenAI:
    base_url, key_name = PROVIDERS[provider]
    api_key = os.getenv(key_name) if key_name else "ollama"  # Ollama ignores the key
    if not api_key:
        raise RuntimeError(f"{key_name} is missing. Copy .env.example to .env and fill it.")
    return OpenAI(base_url=base_url, api_key=api_key, timeout=config.LLM_TIMEOUT_SECONDS)


def chat(client: OpenAI, system: str, user: str, model: str = config.LLM_MODEL) -> str:
    """Send one system + user message, return the reply text."""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=0,  # same input -> (almost) same output; needed for fair evals
    )
    return response.choices[0].message.content or ""
```

---

## Step 1a.7: `src/docpilot/rag.py`

**Goal:** glue: question in, answer plus sources out.

```python
"""The naive RAG pipeline: embed question, search, build prompt, ask the LLM."""
from docpilot import config
from docpilot.embedder import embed_query
from docpilot.llm import chat
from docpilot.vector_store import search

# Decision D-008: this prompt is our first (weak) guardrail.
SYSTEM_PROMPT = f"""You answer questions about technical documentation.
Use ONLY the numbered context. Cite every fact with its number, like [1] or [2].
If the context does not contain the answer, reply exactly:
{config.NOT_FOUND_PHRASE}"""


def build_context(hits: list[dict]) -> str:
    """Number each chunk so the model can cite it: [1] (source) text ..."""
    parts = []
    for number, hit in enumerate(hits, start=1):
        parts.append(f"[{number}] (source: {hit['source']})\n{hit['text']}")
    return "\n\n".join(parts)


def ask(question: str, qdrant_client, llm_client) -> dict:
    query_vector = embed_query(question)
    hits = search(qdrant_client, config.COLLECTION_NAME, query_vector, config.TOP_K)
    user_prompt = f"Context:\n{build_context(hits)}\n\nQuestion: {question}"
    answer = chat(llm_client, SYSTEM_PROMPT, user_prompt)
    return {"answer": answer, "sources": hits}
```

---

## Step 1a.8: scripts

| Script | What it does | Run |
|---|---|---|
| `scripts/01_download_docs.py` | Downloads four FastAPI tutorial pages (raw Markdown from the FastAPI GitHub repo) into `data/docs/fastapi/`. Uses `urllib` from the standard library, so no new dependency. VERIFY the URLs. | `python scripts/01_download_docs.py` |
| `scripts/02_ingest.py` | `load_documents` -> `fixed_size_chunks` for each doc -> `embed_documents` -> `create_fresh_collection` -> `add_chunks`. Prints doc count and chunk count. | `python scripts/02_ingest.py` |
| `scripts/03_ask.py` | Takes a question from the command line, prints the answer, then each source with score and the first 200 characters, so you can **see** what was retrieved. | `python scripts/03_ask.py "How do I make a query parameter optional?"` |

**Done when:** `03_ask.py` prints an answer with `[n]` citations, and the printed sources
match the citations. The doc reports about 51 chunks at 800/100 from four pages; record the
count you actually get.

Continued in [2_phase_1_baseline.md](2_phase_1_baseline.md)

# DocPilot Architecture (Part 1 of 2)

This is the **target** architecture: what DocPilot looks like when Phase 7 is done.
Section 13 (in part 2) shows how it grows phase by phase, so you always know which parts
exist today.

Part 1: the big picture, the pieces, the ingestion pipeline, the data shapes.
Part 2: the question path, agents, guardrails, LLM layer, evals, operations, deployment.

---

## 1. The whole system in one analogy

Think of DocPilot as a **reference library with careful staff**.

| Library | DocPilot | Code lives in |
|---|---|---|
| Staff who stock the shelves at night | Ingestion pipeline | `src/docpilot/ingestion/` |
| The catalogue cards (by meaning and by keyword) | Dense and sparse vectors in Qdrant | Qdrant collections |
| Security guard at the door | Input guardrails | `src/docpilot/guardrails/input_guards.py` |
| Front desk that decides who helps you | Router / supervisor agent | `src/docpilot/agents/` |
| Librarian who fetches books | Retrieval (hybrid + rerank) | `src/docpilot/retrieval/` |
| Librarian who checks "are these the right books?" | Document grader | `agents/nodes` |
| Writer who answers using only those books | Generator (LLM) | `agents/nodes`, `llm/` |
| Fact-checker | Groundedness check | `agents/nodes` |
| Senior librarian you call when unsure | Human-in-the-loop reviewer | `agents/human_review.py`, `api/review_routes.py` |
| Quality checker at the exit | Output guardrails | `guardrails/output_guards.py` |
| The exam the library sits every month | Evals | `evals/` |
| CCTV and the visitor counter | Tracing, metrics, dashboards | `observability/`, Grafana |

Two jobs happen at different times:

- **Write path (offline, rare):** read docs, cut into chunks, turn into vectors, store.
  Runs when docs change. No user is waiting.
- **Read path (online, every question):** a user is waiting, so it must be fast, safe,
  and capped.

Keeping these separate is a key design choice: slow, expensive work (parsing, embedding,
contextual chunking) happens once in the write path, never while a user waits.

---

## 2. Level 1: system context (who talks to DocPilot)

```text
                 ┌────────────────────┐
                 │  Developer (user)  │   asks questions via UI, curl, or MCP client
                 └─────────┬──────────┘
                           │ HTTPS
                           ▼
 ┌──────────────┐   ┌─────────────────────────────┐   ┌──────────────────────────┐
 │ Human        │──▶│          DocPilot           │──▶│ Free LLM providers       │
 │ reviewer     │   │ (API + agents + search +    │   │ Groq / Gemini /          │
 │ (approve,    │◀──│  guardrails + evals)        │   │ OpenRouter / Ollama      │
 │  edit,reject)│   └──────┬───────────────▲──────┘   └──────────────────────────┘
 └──────────────┘          │               │
                           │ download      │ code, CI, images
                           ▼               │
               ┌──────────────────┐  ┌─────┴───────────────┐
               │ Official docs    │  │ GitHub (Actions,    │
               │ websites / repos │  │ Container Registry) │
               └──────────────────┘  └─────────────────────┘
```

**External dependencies and what happens if each disappears:**

| Dependency | If it is down | Our protection |
|---|---|---|
| Groq | Fallback to Gemini, then OpenRouter, then local Ollama | LLM gateway (Phase 7) |
| Docs websites | Only ingestion fails; questions keep working | Data already indexed |
| GitHub | Cannot deploy; running system unaffected | n/a |
| Hugging Face (model download) | Containers would fail to start | Bake model files into the image (Phase 7) |

---

## 3. Level 2: containers (what runs on the server)

In production everything runs as Docker containers started by one `docker-compose.yml`.

```text
 Internet
    │ :443 (HTTPS)
    ▼
┌─────────┐      ┌───────────────────────────────────────────────────────────────┐
│ caddy   │─────▶│ api  (FastAPI + Uvicorn, LangGraph inside, models on CPU)      │
│ TLS,    │ :8000│                                                                │
│ reverse │      └──┬──────────┬──────────┬───────────┬─────────────┬─────────────┘
│ proxy   │         │          │          │           │             │
└─────────┘         ▼          ▼          ▼           ▼             ▼
               ┌────────┐ ┌────────┐ ┌──────────┐ ┌─────────┐ ┌─────────────┐
               │ qdrant │ │ redis  │ │ postgres │ │ tracing │ │ LLM APIs    │
               │ :6333  │ │ :6379  │ │ :5432    │ │ (D-009) │ │ (external)  │
               └────────┘ └────────┘ └──────────┘ └─────────┘ └─────────────┘
                                                        ▲
               ┌────────────┐  scrapes /metrics  ┌──────┴──┐
               │ prometheus │◀───────────────────│  api    │
               │ :9090      │                    └─────────┘
               └─────┬──────┘
                     ▼
               ┌────────────┐
               │ grafana    │  dashboards (behind Caddy, password protected)
               │ :3000      │
               └────────────┘
     optional: ollama :11434 (local LLM fallback), mcp server (stdio or HTTP)
```

| Container | What it holds | Why this one | Why not the alternative |
|---|---|---|---|
| `caddy` | TLS certificates, routing | Automatic HTTPS with one short config | Nginx needs manual certificate setup (certbot) |
| `api` | Our Python code, embedding model, reranker | One process keeps models loaded in memory once | Separate model server: extra hop, not needed at our scale |
| `qdrant` | Dense + sparse vectors, payloads | Hybrid search and filters in one DB | Chroma: fewer production features. pgvector: hybrid needs more manual work. Pinecone: paid |
| `redis` | Cache entries, rate-limit counters | Shared by all API workers; fast; expiry built in | Python dict: each worker has its own copy, lost on restart |
| `postgres` | LangGraph checkpoints, review queue, API key hashes | Durable, handles many writers | SQLite: fine in dev, weak with concurrent writers |
| `prometheus` | Time series of metrics | Industry standard pull model | Pushing to a SaaS: paid or limited |
| `grafana` | Dashboards | Free, works with Prometheus | Building our own charts: waste of time |
| tracing | Per-request step recordings | See D-009 (Langfuse vs Phoenix) | Print statements: not searchable |

**Ports rule:** only Caddy is exposed to the internet (443, and 80 for the certificate
challenge). Every other port stays on the private Docker network.

---

## 4. Level 3: components inside the code

Target package layout (from `PROJECT_DOCUMENTATION.md` section 17, with file names):

```text
src/docpilot/
├── config.py                  # every setting; reads .env                     (Phase 1)
├── ingestion/                                                                  (Phase 2)
│   ├── loader.py              # files -> Document
│   ├── cleaner.py             # strip HTML noise
│   ├── includes.py            # resolve {* path *} code includes
│   ├── blocks.py              # markdown -> Blocks (heading, para, code, table)
│   ├── metadata.py            # technology, version, doc_type, heading_path
│   ├── pdf_loader.py          # Docling for PDF/HTML
│   ├── tables.py              # extract tables -> DuckDB (Phase 5)
│   ├── manifest.py            # content hashes for incremental ingest (Phase 7)
│   └── chunkers/
│       ├── base.py            # Chunk dataclass, Chunker protocol
│       ├── fixed.py           # strategy 1 (moved from Phase 1 chunker.py)
│       ├── recursive.py       # strategy 2
│       ├── semantic.py        # strategy 3
│       ├── parent_child.py    # strategy 4
│       ├── hierarchical.py    # strategy 5
│       └── contextual.py      # strategy 6
├── embedding/
│   ├── base.py                # Embedder protocol (swappable)
│   ├── dense.py               # sentence-transformers BGE
│   └── sparse.py              # BM25 sparse vectors (FastEmbed)                 (Phase 3)
├── store/
│   ├── base.py                # VectorStore protocol (swappable)
│   └── qdrant_store.py        # collections, upsert, search, filters
├── retrieval/                                                                  (Phase 3)
│   ├── dense_search.py
│   ├── sparse_search.py
│   ├── fusion.py              # hand-written RRF
│   ├── hybrid.py              # Qdrant prefetch + fusion
│   ├── reranker.py            # cross-encoder
│   ├── query_transforms.py    # multi-query, HyDE, step-back, decomposition
│   ├── filters.py             # technology / version filters
│   └── pipeline.py            # one function: question -> ranked chunks
├── llm/
│   ├── base.py                # LLMClient protocol
│   ├── client.py              # OpenAI-compatible client (Phase 1)
│   ├── fallback.py            # hand-written fallback chain (Phase 7)
│   ├── gateway.py             # LiteLLM wrapper (Phase 7)
│   └── budget.py              # per-request call counter
├── agents/                                                                     (Phase 4-5)
│   ├── manual_loop.py         # plain-Python agent loop (teaching version)
│   ├── state.py               # AgentState TypedDict
│   ├── prompts.py             # every prompt in one place
│   ├── nodes_retrieval.py     # router, retrieve, grade, rewrite
│   ├── nodes_generation.py    # generate, check_groundedness
│   ├── human_review.py        # interrupt node
│   ├── graph.py               # builds and compiles the graph
│   ├── supervisor.py          # multi-agent routing (Phase 5)
│   └── specialists/           # researcher, sql_analyst, code_helper, critic
├── tools/                                                                      (Phase 5)
│   ├── calculator.py
│   ├── sql_tool.py
│   ├── web_search.py
│   └── doc_section.py
├── guardrails/                                                                 (Phase 6)
│   ├── input_guards.py        # length, injection patterns, topic scope
│   ├── pii.py                 # Presidio wrapper
│   ├── context_guard.py       # untrusted-context wrapping
│   ├── output_guards.py       # citations, not-found policy, leak scan
│   ├── tool_guards.py         # allowlist, SELECT-only SQL
│   └── library_adapters.py    # NeMo / Guardrails AI / Llama Guard
├── cache/                                                                      (Phase 7)
│   ├── exact_cache.py
│   └── semantic_cache.py
├── api/
│   ├── app.py                 # FastAPI app factory (Phase 1 mini, Phase 7 full)
│   ├── schemas.py             # Pydantic request/response models
│   ├── routes_ask.py          # /ask, /ask/stream
│   ├── routes_review.py       # reviewer endpoints (Phase 5)
│   ├── routes_health.py       # /health, /ready, /metrics
│   ├── auth.py                # API key check
│   └── rate_limit.py          # Redis counters
├── observability/                                                              (Phase 7)
│   ├── logging.py             # JSON logs with request id
│   ├── metrics.py             # Prometheus counters / histograms
│   └── tracing.py             # tracing tool wrapper
└── mcp_server/
    └── server.py              # search_docs, get_doc_section (Phase 5)
```

Note on Phase 1: the doc says start **flat** (`config.py`, `loader.py`, `chunker.py`,
`embedder.py`, `vector_store.py`, `llm.py`, `rag.py` all in `src/docpilot/`). We refactor
into the packages above in Phase 2 step 2.1, once there is a real reason (six chunkers will
not fit in one file under 500 lines).

### 4.1 Dependency direction (who may import whom)

```text
api  ──▶  agents  ──▶  retrieval  ──▶  store, embedding
 │          │              │
 │          ├──▶ llm       └──▶ config
 │          ├──▶ guardrails
 │          └──▶ tools
 └──▶ cache, observability
ingestion ──▶ embedding, store, config      (never imports agents or api)
evals     ──▶ retrieval, agents (read-only use)
```

Rule: arrows only point "down". `retrieval` never imports `api`. This keeps each layer
testable on its own and stops circular imports.

---

## 5. The swappable interfaces

Three things must be swappable (guiding principle 3): the LLM, the embedding model, and
the vector database. We use Python `Protocol` classes: a "shape" that any class can match
without inheriting from anything.

```python
# src/docpilot/embedding/base.py
from typing import Protocol


class Embedder(Protocol):
    """Anything that can turn text into vectors."""

    dimension: int  # size of each vector, e.g. 384 for bge-small

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed chunks for storage (no query prefix)."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Embed one question for search (may add a model-specific prefix)."""
        ...
```

```python
# src/docpilot/store/base.py
from typing import Protocol

from docpilot.ingestion.chunkers.base import Chunk


class SearchHit(Protocol):
    chunk: Chunk
    score: float


class VectorStore(Protocol):
    def create_collection(self, name: str, dimension: int) -> None: ...
    def add_chunks(self, name: str, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...
    def search(self, name: str, query_vector: list[float], top_k: int,
               filters: dict | None = None) -> list[SearchHit]: ...
```

```python
# src/docpilot/llm/base.py
from typing import Protocol


class LLMClient(Protocol):
    def complete(self, system: str, user: str, temperature: float = 0.0,
                 max_tokens: int = 800) -> str:
        """Send one prompt, get the text back. Raises on timeout or provider error."""
        ...
```

Why Protocols and not abstract base classes: the real classes do not need to inherit from
anything, so a test can pass in a tiny fake object. Why not just call the libraries
directly everywhere: then swapping Qdrant for pgvector means editing 20 files instead of one.

---

## 6. Write path: the ingestion pipeline in detail

```text
data/docs/*.md, *.html, *.pdf
        │
        ▼
 1. load            loader.py / pdf_loader.py     file -> Document(text, source, technology)
        │
        ▼
 2. clean           cleaner.py                     remove HTML colour tags, nav junk
        │
        ▼
 3. resolve         includes.py                    {* ../docs_src/x.py *} -> real code block
        │
        ▼
 4. parse           blocks.py                      Document -> [Block(kind, text, heading_path)]
        │                                          kinds: heading, paragraph, code, table, list
        ▼
 5. chunk           chunkers/<strategy>.py         Blocks -> [Chunk]  (code/tables never split)
        │
        ▼
 6. contextualise   chunkers/contextual.py         optional: LLM writes 1-2 lines of context
        │           (cached on disk by chunk hash)
        ▼
 7. embed           embedding/dense.py, sparse.py  Chunk.text -> dense vector + sparse vector
        │
        ▼
 8. store           store/qdrant_store.py          upsert points with payload into collection
        │
        ▼
 9. record          manifest.py                    content hash per doc (skip unchanged next time)
```

| Step | Uses an LLM? | Why / why not |
|---|---|---|
| 1-5 | No | Deterministic code is faster, free, testable, and repeatable |
| 6 | Yes, once per chunk | Only exception; results cached so re-runs cost nothing |
| 7 | No LLM, but an embedding model | Small local model on CPU |
| 8-9 | No | Database writes |

Entry point: `scripts/02_ingest.py --strategy hierarchical --collection docs_hier_v1`.

---

## 7. Data shapes

### 7.1 Document and Block

```python
@dataclass
class Document:
    text: str            # full cleaned text of one file
    source: str          # e.g. "fastapi/query_params.md"
    technology: str      # "fastapi", "docker", ...
    version: str | None  # docs version if known
    doc_type: str        # "tutorial", "reference", "guide"


@dataclass
class Block:
    kind: str                # "heading" | "paragraph" | "code" | "table" | "list"
    text: str
    heading_path: list[str]  # ["Query Parameters", "Optional parameters"]
```

### 7.2 Chunk and its Qdrant payload

```python
@dataclass
class Chunk:
    text: str                      # what gets embedded (may include heading + context)
    source: str
    chunk_number: int              # position inside the source, for citations
    strategy: str                  # "fixed", "recursive", ...
    heading_path: list[str] = field(default_factory=list)
    parent_id: str | None = None   # parent-child strategy only
    has_code: bool = False
    has_table: bool = False
    technology: str = ""
    version: str | None = None
    content_hash: str = ""         # sha256 of text, for dedupe and incremental ingest
```

One Qdrant **point** = one chunk:

| Part of point | Content |
|---|---|
| id | UUID made from `source + strategy + chunk_number` (stable across re-runs) |
| vector `dense` | 384 floats (bge-small) |
| vector `sparse` | indices + values (BM25 weights), Phase 3 |
| payload | every Chunk field above, plus `display_text` (text without added context) |

Payload indexes on `technology`, `version`, `doc_type` so filters are fast.

### 7.3 Collection naming

`docs_<strategy>_<embedder>_v<n>`, for example `docs_fixed_bgesmall_v1`.
One collection per chunking strategy (and per embedding model in Phase 3), so the same eval
compares them fairly. Phase 1 uses the name `docpilot_naive` from the doc.

### 7.4 Golden dataset item (JSONL, one per line)

Defined in `PROJECT_DOCUMENTATION.md` section 14.2: `id`, `question`, `type`,
`should_answer`, `reference_answer`, `evidence` (doc + verbatim snippet), `difficulty`,
`split`, `notes`.

Continued in [2_architecture.md](2_architecture.md)

# Phase 3: Retrieval Upgrade (Implementation Plan)

**Goal of the phase:** find the right chunks more often and rank them higher, using
hybrid search, reranking, query transforms, a better embedding model if it earns its cost,
and metadata filters. Also: learn Docker, and build the generation eval harness that
Phase 4 needs.

**Teaching companion:** `docs/teaching/phase_3_retrieval.md` (includes the Docker primer)

**Ablation rows:** `C-sparse` (sparse only, for learning), C6 hybrid (RRF), C7 + reranker,
C8 + best query transform, plus embedding-model rows. All on the Phase 2 winning chunking.

```text
Phase 3 retrieval pipeline (retrieval/pipeline.py)

question ─▶ [query transform?] ─▶ [filters?] ─┬─▶ dense search  (top 50) ─┐
                                              └─▶ sparse search (top 50) ─┴─▶ RRF ─▶ top 30
                                                                                     │
                                                         [reranker?] cross-encoder ◀─┘
                                                                     │
                                                               final top 4-5
```

---

## Step 3.1: Docker primer, then Qdrant in Docker

**Goal:** Qdrant runs as a server, so the API, scripts, and evals can use it at the same
time (local mode allows only one process, D-003).

1. Install Docker Desktop (free for personal use; VERIFY current terms) with WSL 2.
2. Primer exercises (teaching file section 2): `docker run hello-world`, images vs
   containers, ports, volumes, `docker ps`, `docker logs`, `docker compose up -d`.
3. **File:** `docker-compose.yml` (only Qdrant for now)

```yaml
# docker-compose.yml (Phase 3 version: one service)
services:
  qdrant:
    image: qdrant/qdrant:vX.Y.Z      # VERIFY: pin an exact tag, never "latest"
    ports:
      - "6333:6333"                   # REST API + web dashboard at http://localhost:6333/dashboard
    volumes:
      - ./qdrant_storage:/qdrant/storage   # data survives container restarts (gitignored)
    restart: unless-stopped
```

4. `config.py`: add `QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")`;
   `get_client()` uses `QdrantClient(url=...)` when set, local path otherwise.
5. Re-index the winning strategy into Docker Qdrant and re-run its eval.

**Done when:** numbers match the local-mode run (same data, same model: they should).
Also check: does the Qdrant image publish an `arm64` build? (Needed for the free ARM VM.)
Record the answer in `decisions.md`.

---

## Step 3.2: Sparse (keyword) vectors

**Goal:** a keyword searcher that is strong on exact identifiers like `max_length`.

1. **Raw first:** `labs/lab3_bm25.py`: write BM25 by hand over 5 sentences (term
   frequency, inverse document frequency, length normalisation) and print scores.
   No new dependency.
2. **Then the library:** FastEmbed's BM25 sparse model (`Qdrant/bm25`, VERIFY name and API)
   produces sparse vectors (a short list of word ids and weights).
3. **File:** `src/docpilot/embedding/sparse.py` with `embed_sparse_documents(texts)` and
   `embed_sparse_query(text)`.
4. Collection now has **named vectors**: `dense` and `sparse` (sparse with the IDF
   modifier, VERIFY).

```python
# store/qdrant_store.py (sketch)   VERIFY every name against installed qdrant-client
client.create_collection(
    collection_name=name,
    vectors_config={"dense": models.VectorParams(size=dim, distance=models.Distance.COSINE)},
    sparse_vectors_config={"sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)},
)
```

5. Eval sparse-only as `C-sparse`. Compare per question type with dense-only: expect
   different winners on "exact identifier" vs "paraphrase" questions, but **record what
   you actually get**.

---

## Step 3.3: Hybrid with hand-written RRF

**File:** `src/docpilot/retrieval/fusion.py`

```python
"""Reciprocal Rank Fusion: merge ranked lists using ranks only, not scores."""


def reciprocal_rank_fusion(ranked_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Each list holds chunk ids, best first. Returns (id, fused_score), best first.

    Why ranks and not scores: cosine scores (0..1) and BM25 scores (0..any number)
    are on different scales. Ranks are always comparable.
    k = 60 is the common default; a bigger k flattens the advantage of rank 1.
    """
    fused: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, chunk_id in enumerate(ranked, start=1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda item: item[1], reverse=True)
```

**Files:** `retrieval/dense_search.py`, `retrieval/sparse_search.py` (each returns ids +
payloads), `retrieval/hybrid.py` (`hybrid_search_manual()`: both top 50, RRF, top k).

**Test:** `tests/test_fusion.py`: an id ranked first in both lists wins; an id in only one
list still appears; equal ranks give equal scores.

**Eval:** row **C6** (manual RRF). Try k = 60 and one other value, record both.

---

## Step 3.4: Hybrid with Qdrant's server-side fusion

**Goal:** the same idea, done inside the database in one call (fewer round trips).

```python
# retrieval/hybrid.py (sketch)   VERIFY: Query API with prefetch + fusion in the docs
response = client.query_points(
    collection_name=name,
    prefetch=[
        models.Prefetch(query=dense_vector, using="dense", limit=50),
        models.Prefetch(query=sparse_vector, using="sparse", limit=50),
    ],
    query=models.FusionQuery(fusion=models.Fusion.RRF),
    limit=top_k,
)
```

**Test:** for 10 golden questions, top-5 ids from manual RRF and server RRF are compared.
If they differ, find out why (for example a different `k`) and write it down.
Keep the server version as default if the numbers match, because it is one network call.

---

## Step 3.5: Reranker (cross-encoder)

**File:** `src/docpilot/retrieval/reranker.py`

```python
"""Re-score candidates by reading question and chunk together (slow but accurate)."""
from functools import lru_cache

from sentence_transformers import CrossEncoder   # VERIFY API on installed version

RERANKER_MODEL = "BAAI/bge-reranker-base"         # VERIFY name; compare v2-m3 if time


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    return CrossEncoder(RERANKER_MODEL)


def rerank(question: str, hits: list[dict], keep: int = 5) -> list[dict]:
    pairs = [(question, hit["text"]) for hit in hits]
    scores = get_reranker().predict(pairs)          # one score per (question, chunk) pair
    for hit, score in zip(hits, scores):
        hit["rerank_score"] = float(score)
    hits.sort(key=lambda hit: hit["rerank_score"], reverse=True)
    return hits[:keep]
```

**File:** `evals/timing.py`: helper that records milliseconds per stage and reports p50 and
p95 over the dev set.

**Eval:** row **C7** with candidates = 20, 30, 50. Record Recall@5, MRR **and** p50/p95
latency on this CPU for each. The trade-off table (quality vs latency) is the deliverable.

---

## Step 3.6: Query transforms

**File:** `src/docpilot/retrieval/query_transforms.py` (prompts in `prompts/` or at top)

| Transform | Function | LLM calls | Idea |
|---|---|---|---|
| Multi-query | `multi_query(q, n=3)` | 1 | Write 3 rewrites; search each; RRF all lists |
| HyDE | `hyde(q)` | 1 | Write a fake answer; embed and search with it |
| Step-back | `step_back(q)` | 1 | Ask a more general question; search both |
| Decomposition | `decompose(q)` | 1 | Split multi-part question into sub-questions; search each |

**Make the eval repeatable:** cache each transform's output in
`evals/cache/transforms_<name>_<model>.json` keyed by question. The first run spends LLM
calls; later runs are free and deterministic.

**Eval:** one row per transform (`C8-multi`, `C8-hyde`, ...), with LLM calls per question
and latency. **C8** = the best one, only if it beats C7. If none beats C7, C8 = C7 and we
record "no transform kept": a negative result worth talking about.

---

## Step 3.7: Embedding model comparison

**File:** `scripts/05_compare_embedders.py`

Models: `bge-small` (baseline), `bge-base`, `bge-m3`, `nomic-embed-text`, an `e5` model.
Each has its own prefix rules (for example some expect `query:` / `passage:`): VERIFY on
each model card and put them in a per-model settings dict. Wrong prefixes quietly lower
scores, so this is a classic bug.

Report per model: dimension, Recall@5, MRR, index time for the corpus, query embedding
latency p50, RAM. Keep `bge-small` unless another model's gain is worth its cost. Update
D-002 with the numbers either way.

---

## Step 3.8: Metadata filtering

**File:** `src/docpilot/retrieval/filters.py`

1. Payload indexes on `technology`, `version`, `doc_type` (VERIFY `create_payload_index`).
2. `extract_filters(question) -> dict`: v1 is plain keyword matching on technology names
   ("docker", "pydantic"). The Phase 4 router can later extract filters with an LLM.
3. Golden items gain an optional `technology` field; eval runs with filters on vs off.

---

## Step 3.9: Generation eval harness v0 (decision D-014)

**File:** `evals/run_generation_eval.py`, prompts in `evals/judge_prompts.py`

| Metric | How (plain-Python first, Rule 8) |
|---|---|
| Faithfulness | Judge LLM lists the claims in the answer, then marks each supported / not supported by the context. Score = supported / total |
| Answer relevancy | Judge answers "does this answer address the question?" on a 1-5 scale with a reason |
| Abstention accuracy | Deterministic phrase check (from Phase 1) |
| Answer correctness | Judge compares answer to `reference_answer` (yes / partly / no) |

Rules (Rule 11): judge model differs from generator when possible; temperature 0; judge
model name saved in results; `evals/spot_checks/<run>.md` holds about 20% of items checked
by hand (agree / disagree with the judge). Report judge agreement rate.

Run on C0 and the current best config only (free-tier tokens are limited).
RAGAS / DeepEval come in Phase 4.5 and are compared against this harness.

---

## Step 3.10: `retrieval/pipeline.py` (one front door)

```python
def retrieve(question: str, settings: RetrievalSettings) -> list[dict]:
    """The only retrieval function the rest of the system calls.
    settings says: hybrid on/off, reranker on/off, candidates, transform, filters."""
```

`RetrievalSettings` is a small dataclass; its default values are the winners from this phase.
Evals, agents, the API, and the MCP server all call this one function.

---

## Phase 3 gate

- [ ] Qdrant in Docker; arm64 support checked and recorded
- [ ] rows: C-sparse, C6 (manual + server), C7 (with latency), C8 variants, embedding models
- [ ] generation metrics for C0 and best config, judge named, spot-check file exists
- [ ] defaults chosen in `RetrievalSettings` with evidence in `decisions.md`
- [ ] versions pinned: Docker image tag, fastembed, reranker model revision
- [ ] interview notes; `git tag phase-3`

# Teaching Notes, Phase 1: Naive Baseline, Evals, Mini API

Plan files: `docs/implementation_plan/phase_1_baseline.md`, `2_phase_1_baseline.md`

---

## 1. What RAG is

**Like I'm five:** an open-book exam. A plain chatbot answers from memory: fast, but it may
make things up. RAG first **finds the right pages in the book**, then writes the answer
**only from those pages**, and says which page each fact came from.

**What it really is:** Retrieval-Augmented Generation.
Retrieval = search your documents for the pieces most related to the question.
Generation = an LLM writes the answer with those pieces pasted into its prompt.

**Why RAG and not fine-tuning:**

| | RAG | Fine-tuning |
|---|---|---|
| Docs change | Re-index (minutes) | Retrain (hours, money) |
| Citations | Yes, you know which chunk was used | No: knowledge is mixed into weights |
| Hallucination control | Can abstain when nothing relevant is found | Hard |
| Cost here | Free | GPU we do not have |

Fine-tuning teaches **style and behaviour**; RAG supplies **facts**. They can be combined,
but for "answer from these docs with sources", RAG is the right tool.

---

## 2. Following one question through the Phase 1 files

```text
03_ask.py "How do I make a query parameter optional?"
  │
  ├─ rag.ask()
  │    ├─ embedder.embed_query()      question + BGE prefix -> 384 numbers
  │    ├─ vector_store.search()       Qdrant finds 4 nearest chunk vectors
  │    ├─ rag.build_context()         "[1] (source: ...) text..." x 4
  │    └─ llm.chat()                  system prompt + context + question -> LLM
  │
  └─ prints answer + the 4 sources with scores
```

And ingestion, run once before:

```text
02_ingest.py: loader.load_documents() -> chunker.fixed_size_chunks() per doc
              -> embedder.embed_documents() (batches of 32)
              -> vector_store.create_fresh_collection() -> add_chunks()
```

---

## 3. Chunking: why cut documents at all

**Like I'm five:** if you summarise a whole book in one sentence, you lose the details.
If you summarise each paragraph, each summary is sharp.

**What it really is:** one embedding per whole page blurs many topics into one vector, so
it matches everything a little and nothing well. Small chunks give sharp vectors. Too
small, and a chunk lacks context ("it" with no idea what "it" is). Size is a trade-off we
**measure** in Phase 2.

**Overlap:** with 800-character chunks and 100 overlap, each new chunk starts 700
characters after the last. A sentence cut at a boundary appears whole in at least one
chunk (if it is shorter than the overlap).

**Why fixed-size is a deliberately weak baseline (D-006):** it cuts code and tables in
half. We want an honest "before" number. Starting with the best strategy would hide what
each improvement is worth.

---

## 4. The vector database

**Like I'm five:** a giant notebook of map coordinates. You give it a new coordinate (your
question) and it instantly tells you the 4 closest entries.

**What it really is:** Qdrant stores **points**. Each point = id + vector + payload (any
JSON: our text, source, chunk number). Search = "nearest vectors to this query vector".

**How is it fast?** Comparing against every vector works for 50 chunks, not for 5 million.
Qdrant builds an **HNSW** index (a layered graph of "neighbours of neighbours") that finds
very close vectors without checking all of them. It is **approximate** nearest neighbour
search: it can, rarely, miss the exact best one in exchange for huge speed. At our size it
behaves almost exactly like exact search.

**Local mode vs server mode:** `QdrantClient(path=...)` runs Qdrant inside your Python
process and saves files to a folder. Easy, no Docker. Limit: only one process can open the
folder at a time, so the API and the ingest script cannot both run. Phase 3 moves to the
Docker server.

**Why Qdrant (D-003):**

| Option | Why not (now) |
|---|---|
| Chroma | Very easy, but fewer production features (sparse + dense hybrid in one query, rich filters) |
| pgvector | Excellent if you already run Postgres; hybrid search needs more manual work |
| FAISS | A library, not a database: no payloads, no server, no filters out of the box |
| Pinecone | Managed and good, but paid beyond small limits and not self-hostable |

**Stable ids:** we make ids with `uuid5(source#chunk_number)`. Same chunk, same id, every run.
Re-running ingestion overwrites instead of creating duplicates.

---

## 5. The prompt and the LLM

**System prompt** (D-008) says: use only the context, cite `[n]`, otherwise say exactly
"I could not find this in the documents." This is our first, weak guardrail. LLMs follow
it most of the time, not always. Phase 6 measures how often it fails.

**Numbered context:** each chunk gets `[1]`, `[2]`... so the model can cite it, and we can
map `[2]` back to a real source. Citations are only meaningful if numbers map to real chunks
(Phase 6 checks this automatically).

**Temperature 0:** the model picks its most likely next token each time. Answers become
(nearly) repeatable, which is essential for fair evaluation. It is not perfectly
deterministic on hosted APIs, so we still record one run's results with date and model.

**Why one OpenAI-compatible client (D-004):** Groq, OpenRouter, Ollama, and Gemini all
accept the same request format at different URLs. Switching provider = changing `.env`.
The `openai` Python package is just a well-made HTTP client here; no OpenAI account is used.

---

## 6. Inspecting failures before measuring (step 1b)

Numbers tell you **how much** is wrong; reading failures tells you **what** is wrong.
Engineers who skip this step tune blindly. In the FastAPI docs you will likely see:
include markers instead of code, chunks cut through HTML styling, colour tags in text.
Write what you see in your own words. These become Phase 2 tasks.

---

## 7. Evals: the exam for your AI

**Like I'm five:** you cannot say a student improved without giving the same exam before and
after. The golden dataset is the exam; the metrics are the marking scheme.

### 7.1 Golden dataset rules and why

| Rule | Why |
|---|---|
| Written by hand, every item reviewed | Wrong answer keys produce confident nonsense numbers |
| Cover every question type | Averages hide where you fail; per-type results show it |
| ~15% unanswerable | Tests whether the system can say "not found" |
| Evidence = doc + verbatim snippet (D-010) | Chunk ids change with every chunking strategy; a snippet does not. One answer key works for all strategies |
| dev / test split | Tuning on the exam you report is cheating yourself (overfitting). Test is opened only at gates |

### 7.2 Metrics with tiny worked examples

Say for one question the top 5 retrieved chunks are marked relevant (1) or not (0):
`[0, 1, 0, 0, 1]`.

- **Recall@k (hit rate):** was there **any** relevant chunk in the top k?
  @1 -> 0, @2 -> 1, @5 -> 1. Average over questions = share of questions where the
  answer was findable. If retrieval misses, the LLM cannot answer: this is the first
  number to watch.
- **MRR (mean reciprocal rank):** 1 / rank of the **first** relevant chunk. Here rank 2, so
  0.5. Average over questions. Rewards putting the right chunk first.
- **nDCG@k:** gives credit for every relevant chunk, discounted by position:
  `1/log2(rank+1)`. Rank 1 gets 1.0, rank 2 gets 0.63, rank 5 gets 0.39. Divide by the
  best possible score (ideal order) so the result is between 0 and 1.

(These are arithmetic examples of the formulas, not results from our system.)

**Why three metrics?** Recall says "is it there?", MRR says "is it first?", nDCG says "are
all the useful ones near the top?". A change can improve one and hurt another.

### 7.3 Matching: "is this chunk a hit?"

A chunk is a hit if it contains the gold snippet (after lowercasing and squashing spaces),
or at least 70% of it as one continuous piece (handles snippets cut by a chunk boundary).
Each snippet counts once, so two overlapping chunks with the same snippet do not double
the score. The 70% threshold is a setting we record with every result.

### 7.4 Abstention

Abstention accuracy = how often the system says "not found" exactly when it should.
We check by looking for the exact phrase: deterministic, no judge needed. Both mistakes
matter: answering an unanswerable question (hallucination) and refusing an answerable one.

### 7.5 Why retrieval metrics first

They are **deterministic** (same input, same number), **free** (no LLM calls), and **fast**.
Generation metrics need an LLM judge (noisy, rate-limited). So retrieval metrics become the
CI gate later (D-011).

---

## 8. FastAPI primer (step 1e)

**Like I'm five:** an API is a restaurant counter. Customers (programs) hand in an order
in an agreed format (JSON); the kitchen (your code) returns a dish in an agreed format.

| Concept | In our code | What it does |
|---|---|---|
| App | `app = FastAPI(...)` | The server object |
| Route | `@app.post("/ask")` | Which function handles which URL and method |
| Request model | `AskRequest(BaseModel)` | Pydantic checks types and limits; bad input gets `422` automatically |
| Response model | `response_model=AskResponse` | Shapes and documents the output |
| Automatic docs | `/docs` | Interactive page generated from your models |
| Lifespan | `lifespan()` | Code that runs once at start (open DB, load models) and once at shutdown |
| Uvicorn | `uvicorn docpilot.api:app --reload` | The program that actually listens on the port |

**`def` vs `async def`:** a plain `def` endpoint runs in a thread pool, so slow blocking
work (model, HTTP call with a sync client) does not freeze the server. `async def` is
faster for many waiting network calls, **but** a blocking call inside `async def` freezes
everything. Beginners often write `async def` and then call blocking code. We stay with
`def` until Phase 7 where we do async properly.

**Status codes to know:** 200 OK, 401 not authenticated, 422 validation error, 429 too many
requests, 500 server bug, 503 dependency down.

**Why FastAPI and not Flask:** type-checked requests via Pydantic, automatic docs, and
native async. Flask can do these with add-ons; FastAPI has them built in, and it is what
most AI job descriptions list.

**Testing with fakes:** in `tests/test_api.py` we replace `ask` with a fake function, so
the test checks **our API code** (validation, response shape) without needing the model or
an API key. Fast, free, reliable.

---

## 9. Self-check

1. Explain RAG with the open-book analogy, then precisely. Why not fine-tuning?
2. Walk through `03_ask.py` file by file.
3. What does overlap protect against? What does it cost?
4. What is HNSW and why is search "approximate"?
5. Why stable point ids?
6. For relevance `[0, 0, 1, 0]`: Recall@1, Recall@3, reciprocal rank?
7. Why label evidence by snippet and not by chunk id?
8. Why keep a test split you rarely look at?
9. What happens if you call blocking code inside `async def`?

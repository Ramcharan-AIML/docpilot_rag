# Teaching Notes, Phase 3: Retrieval Upgrade (+ Docker primer, + LLM-as-judge)

Plan file: `docs/implementation_plan/phase_3_retrieval.md`

---

## 1. Docker primer

**Like I'm five:** a shipping container. Whatever is inside (a car, bananas) the ship,
crane, and truck handle it the same way. A Docker container packs your program **with
everything it needs** (Python version, libraries, settings), so it runs the same on your
laptop, in CI, and on the cloud VM.

| Word | Meaning | Analogy |
|---|---|---|
| Image | A read-only template (filesystem + start command) | A recipe / a frozen meal |
| Container | A running copy of an image | The meal, heated and served |
| Dockerfile | Instructions to build an image | The recipe card |
| Registry | Where images are stored (Docker Hub, GHCR) | The supermarket freezer |
| Port mapping `6333:6333` | Host port -> container port | A door from your house into the container |
| Volume `./qdrant_storage:/qdrant/storage` | Folder that survives container deletion | A storage unit outside the house |
| Compose | One YAML file that starts several containers together | A party plan for several caterers |

**Container vs virtual machine:** a VM includes a whole operating system (heavy, minutes to
start). A container shares the host's kernel and only packs the app (light, seconds to
start).

**Why Qdrant moves to Docker now:** local mode allows one process. With a server, the API,
ingest script, and evals can all connect at once. It is also how production runs it.

**Why pin image tags (never `latest`):** `latest` changes under you. A pinned tag is a
pinned version, same reason as `requirements.txt`.

**Commands to know:** `docker ps`, `docker logs <name>`, `docker compose up -d`,
`docker compose down`, `docker compose ps`, `docker exec -it <name> sh`.

**Two CPU architectures:** the AWS server we plan to use (`m7i-flex.large`) is x86 (amd64);
the Oracle VM we move to later is ARM (arm64). An image built only for one will not run on
the other. Check every image now, not on deploy day.

**Also in Compose this phase:** SeaweedFS (S3-compatible storage, used with boto3) and the
MLflow server. Read `primer_object_storage.md` and `primer_mlflow.md`.

---

## 2. BM25 and sparse vectors

**Like I'm five:** a word-matching game with smart scoring. Matching a rare word like
`max_length` scores big; matching "the" scores almost nothing. And a short page that
mentions your word twice beats a giant page that mentions it twice among thousands of words.

**What BM25 really scores** (for each question word found in a chunk):

```text
score += IDF(word) × (tf × (k1 + 1)) / (tf + k1 × (1 - b + b × chunk_length / average_length))
   IDF  = how rare the word is across all chunks (rare -> big)
   tf   = how many times the word appears in this chunk (more -> bigger, but it saturates)
   k1   = how fast repeated words stop adding score (often ~1.2-2.0)
   b    = how much long chunks are penalised (often ~0.75)
```

You write this by hand in `labs/lab3_bm25.py` first, then use the library.

**Sparse vector:** imagine a vector with one slot per word in the vocabulary (tens of
thousands of slots). A chunk uses only a few words, so almost every slot is zero.
We store only the non-zero slots: `{word_id: weight}`. That is "sparse". Dense vectors
(384 numbers, all non-zero) are the opposite.

**Why sparse vectors inside Qdrant and not `rank_bm25` in Python:** one database holds both
kinds, and it can merge results server-side. `rank_bm25` keeps everything in memory in one
process: fine for a lab, not for a service.

---

## 3. Hybrid search and RRF

**Like I'm five:** you ask two friends for restaurant tips. One is great with names ("the
place called X"), one understands vibes ("somewhere cosy"). You trust a place most if
**both** put it near the top of their lists.

**Why we cannot just add the scores:** cosine is between -1 and 1; BM25 can be 0 to 30 or
more. Adding them lets BM25 shout over cosine. Normalising scores is fiddly and fragile.

**RRF uses ranks only:** `score = sum of 1 / (k + rank)` over the lists.
Worked arithmetic with k = 60 (an example of the formula, not a project result):

```text
chunk A: rank 1 in dense, rank 3 in sparse -> 1/61 + 1/63 = 0.0164 + 0.0159 = 0.0323
chunk B: rank 2 in dense, missing in sparse -> 1/62           = 0.0161
chunk C: missing in dense, rank 1 in sparse -> 1/61           = 0.0164
order: A, C, B   (A wins because both friends liked it)
```

**What k does:** a small k makes rank 1 much more valuable than rank 5; a big k flattens the
difference. 60 is the common default from the original paper; we try one other value.

**Manual first, then Qdrant's built-in fusion:** writing it by hand means you can explain
it; the server version does the same in one network call. If the two disagree, finding out
why is a great learning moment.

---

## 4. Rerankers: bi-encoder vs cross-encoder

**Like I'm five:** the first search is a quick scan of 5,000 CVs by keywords and a photo:
fast but rough. The reranker is the interview: you sit with each of the top 30 candidates
and really talk. Much slower, much more accurate, so you only do it for a shortlist.

| | Bi-encoder (our embedder) | Cross-encoder (reranker) |
|---|---|---|
| How | Question and chunk embedded **separately**, compared by cosine | Question and chunk read **together** in one pass, outputs a relevance score |
| Speed | Chunks embedded once at ingest; search is instant | Must run once per (question, chunk) pair at question time |
| Accuracy | Good | Better: it sees how question words relate to chunk words |
| Use | First pass over everything | Second pass over top 20-50 |

**Cost on CPU:** reranking 50 chunks means 50 model passes per question. That is why we
measure p50/p95 latency for 20, 30, and 50 candidates and choose with data.

**Why not Cohere Rerank:** paid. `bge-reranker` models are free and run locally.

### 4b. The simple version (step 3.5, written for the learner on 2026-10-22)

**1. What a reranker does**
- Search turns the question into numbers, and each chunk into numbers, **separately**.
  Then it compares the numbers. Fast, but the model **never reads the question and the
  chunk together**.
- A reranker reads **question + chunk together**, like a teacher reading each answer
  sheet, and gives one score: "how well does this chunk answer this question?"
- Very accurate, but **slow**: one model run per chunk.

**2. Why use both**
1. Search quickly picks about 30 candidates out of 453 chunks (fast).
2. The reranker carefully re-orders only those 30 (slow but accurate).
3. We keep the best ones.

Like a job interview: HR quickly shortlists 30 CVs, then the manager reads only those 30
carefully. The trade-off we measure: more candidates (20, 30, 50) = more chances to find the
right chunk, but more waiting time.

**3. What we built**

| File | What it does |
|---|---|
| `src/docpilot/retrieval/reranker.py` | `rerank()`: scores each (question, chunk) pair, sorts, keeps the best; remembers each chunk's old place (`search_rank`) |
| `src/docpilot/config.py` | model `BAAI/bge-reranker-base`, revision pinned |
| `evals/timing.py` | measures time per stage: embed, search, rerank (p50 / p95) |
| `evals/run_retrieval_eval.py` | option `--rerank N` (rerank the top N) |
| `tests/test_reranker.py` | 5 tests with a fake model (no 1.1 GB download in CI) |

No new library: `sentence-transformers` was already installed. Real results: rows C7 in
`evals/ABLATION.md` and section 50 of `docs/4_USER_GUIDE.md`.

---

## 5. Query transforms

The user's question is not always a good search query.

| Transform | Like I'm five | Helps when | Costs |
|---|---|---|---|
| Multi-query | Ask the same thing three different ways and pool the answers | Vague wording | 1 LLM call + 3 searches |
| HyDE | Imagine what the answer page would say, then search for pages like that | Short questions; questions phrased very unlike the docs | 1 LLM call; can mislead if the imagined answer is wrong |
| Step-back | Before "why does X fail with Y?", ask "how does X work?" | Questions needing background | 1 LLM call + 2 searches |
| Decomposition | Split "compare A and B" into "what is A?" and "what is B?" | Multi-part and comparison questions | 1 LLM call + N searches |

**Each one is an experiment.** Many do **not** help on clean technical docs. Keeping none is
a valid, honest outcome, and good interview material.

**Caching transforms for repeatable evals:** LLM outputs vary slightly. We save each
rewritten query to a file, so later eval runs reuse the exact same rewrites (free and
deterministic).

### 5b. The simple version (step 3.6, 2026-10-22)

**What it does:** before we search, the LLM changes the question into better search words.
Then we search with the **original question AND the new text**, and mix the lists with RRF
(like dense + sparse in 3.3). The reranker still judges against the **original** question.

**Why the original is always kept:** a bad rewrite can then only add noise; it cannot throw
away what the plain search already found.

**HyDE trap:** the fake answer is a **passage**, not a question, so it is embedded like a
chunk (no BGE question prefix). Using the question prefix on it would be a quiet bug.

**What we built**

| File | What it does |
|---|---|
| `src/docpilot/retrieval/query_transforms.py` | the 4 prompts and `transform()`; cleans the LLM's lines |
| `src/docpilot/retrieval/hybrid.py` | `multi_search()`: one Qdrant hybrid search per text, RRF over the lists |
| `evals/transform_cache.py` | saves each LLM output in `evals/cache/`; waits and retries on Groq rate limits |
| `evals/run_retrieval_eval.py` | option `--transform multi / hyde / stepback / decompose` |
| `tests/test_query_transforms.py` | 8 tests with a fake LLM (no API key needed) |

---

## 6. Choosing an embedding model with data

Public leaderboards (like MTEB) average many tasks and domains. **Your** docs, **your**
questions, **your** CPU are what matter. So we compare a few models on our own eval:
quality (Recall@5, MRR) against cost (index time, query latency, RAM, vector size).

**Classic bug:** each model family expects different prefixes (BGE instruction, `query:` /
`passage:` for e5, `search_query:` / `search_document:` for nomic). Use the wrong one and
scores drop quietly. Verify each model card.

### 6b. The simple version (step 3.7, 2026-10-22)

**What it does:** the embedding model turns text into numbers (the "meaning" vector). We
try 5 models on **exactly the same 453 chunks** and the same questions, and see which one
finds the right chunk most often, and what it costs.

**Fair test:** we read the chunks back from the app's collection (no re-chunking), use
**dense search only** (hybrid + reranker would hide part of the difference), and give each
model its own prefixes from its model card.

| Short name | Model | Size | Prefix (question / chunk) |
|---|---|---|---|
| bge-small (now) | BAAI/bge-small-en-v1.5 | 133 MB, 384 numbers | BGE instruction / none |
| bge-base | BAAI/bge-base-en-v1.5 | 438 MB, 768 | BGE instruction / none |
| bge-m3 | BAAI/bge-m3 | 2.3 GB, 1024 | none / none |
| e5-base | intfloat/e5-base-v2 | 438 MB, 768 | `query: ` / `passage: ` |
| nomic | nomic-ai/nomic-embed-text-v1.5 | 547 MB, 768 | `search_query: ` / `search_document: ` |

**What we measure:** Recall@5 and MRR (quality); vector size, index time, question
embedding time and RAM (cost). We switch only if the gain is worth the cost.

**What we built:** `evals/compare_embedders.py` (the comparison), `all_payloads()` in
`store/qdrant_store.py` (reads the chunks back), `tests/test_compare_embedders.py` (pins
and prefix rules are checked).

---

## 7. Metadata filtering

**Like I'm five:** asking the librarian "only from the Docker shelf, please".

A filter is applied **inside** the search (Qdrant uses payload indexes), so you still get
k results, all from the right technology. Filtering after search could leave you with 1
result out of 4. Starting simple (keyword matching on technology names) is enough; an LLM
router can extract filters later.

---

## 8. LLM-as-judge (generation evals)

Retrieval metrics check the **search**. Now we check the **answer**.

| Metric | Question it answers | Example of failing |
|---|---|---|
| Faithfulness | Is every claim supported by the retrieved text? | Answer adds a default value that no chunk mentions |
| Answer relevancy | Does it address the question asked? | Correct facts about path params when asked about query params |
| Answer correctness | Does it match the reference answer? | Says `None` makes it required |
| Abstention accuracy | Says "not found" exactly when it should? | Invents an answer to an unanswerable question |

An answer can be **faithful but irrelevant** (accurate quotes about the wrong thing) or
**relevant but unfaithful** (on topic, but invented). That is why we measure both.

**How the faithfulness judge works:** step 1, list the claims in the answer. Step 2, for
each claim, say whether the context supports it. Score = supported / total. Breaking it
into steps makes the judge more reliable than one "rate this 1-10" question.

**Judges are noisy. Known biases:**
- **Self-preference:** a model tends to like its own writing, so judge with a different model.
- **Verbosity:** longer answers often get higher marks.
- **Position:** when comparing two answers, the first is often preferred.
- **Small models:** inconsistent; run twice and compare.

**Mitigations (Rule 11):** temperature 0, a different and the strongest available free
judge, about 20% spot-checked by hand, judge model always reported, agreement rate
between you and the judge reported.

**Why our own judge before RAGAS/DeepEval:** you will understand what those libraries
compute inside, and you can tell when they are wrong.

---

## 8b. Models in production: laptop vs cloud (learner question, 2026-10-22)

**The 3.5 GB is only the experiment.** Like test-driving 5 cars at the showroom and buying
one: step 3.7 tries 5 embedding models once, on the laptop, to choose. Production ships only
the winners: bge-small (133 MB) + BM25 (0.09 MB) + MiniLM reranker (91 MB) = about 225 MB.

**Two moments:**
- **Ingestion (once, offline):** embed all chunks, store the numbers in Qdrant. Later only
  new or changed documents are embedded again.
- **Each question (live):** embed only the question (about 20-40 ms on the laptop), Qdrant
  search (about 12 ms), rerank the top 20 (about 0.5 s), then the LLM (Groq, outside).

**Yes, the models run in the cloud:** inside the API container, on the server's CPU, the
same code as on the laptop. Two ways to get the files there: **bake them into the Docker
image** (fast start, no internet needed, exact pinned files; image about 300 MB bigger) or
download at first start (smaller image; slow first start, fails if Hugging Face is down).
Rule: **load once at startup, keep in RAM, reuse for every request** (`lru_cache` in
`get_model()` / `get_reranker()`).

| Other way | Why not for us now |
|---|---|
| Separate model server (e.g. Hugging Face TEI) | more moving parts; worth it with heavy traffic |
| Paid API (OpenAI embeddings, Cohere Rerank) | costs money; data leaves our server |
| GPU server | costs money; our small models do not need it |

**What can go wrong in production:**

| Situation | Handling |
|---|---|
| Cold start (first question waits for model loading) | load and warm up at startup |
| Many users at once on few CPU cores | load test (7.16), fewer candidates, cache repeated questions (Redis, 7.3) |
| RAM full (models + Qdrant + Redis + API) | small models; one reason the 1.1 GB reranker lost |
| Changing the embedding model | old chunk vectors and new question vectors no longer match: re-embed all chunks (new collection, then switch) |
| Model files change on Hugging Face | pinned revisions |
| Hugging Face down or rate-limited | bake files into the image |
| Server CPU slower than the laptop | measure again on the server; never assume laptop numbers |
| New documents | incremental ingestion: embed only new or changed chunks (7.17) |

**Summary:** the laptop is the test kitchen (try many recipes); the cloud is the restaurant
(cook only the winner, with small ingredients, loaded once, reused for every customer).

---

## 9. One front door: `retrieval/pipeline.py`

Everyone (evals, agents, API, MCP server) calls one function with one settings object.
If each caller built its own search, they would drift apart and your eval numbers would
no longer describe what users get.

---

## 10. Self-check

1. Image vs container vs volume? Why pin tags? Why do amd64 and arm64 both matter?
2. Explain BM25 in plain words: what do IDF, tf, and length normalisation do?
3. Why can't you add cosine and BM25 scores? Compute RRF for a small example.
4. Bi-encoder vs cross-encoder: speed, accuracy, where each is used?
5. What did the reranker cost in p95 latency on your CPU?
6. Which query transform helped on your data, if any? What did it cost?
7. Faithfulness vs relevancy: give an answer that passes one and fails the other.
8. Name three judge biases and how you reduced each.

# DocPilot User Guide (Part 2)

Continues [USER_GUIDE.md](USER_GUIDE.md), which hit the 500-line limit (Rule 12). Part 1
holds the project overview, Phase 0, steps 1a.1 and 1a.2, daily commands and the concept
table. Phase 1 steps from 1a.3 on are written here.

---

## 16. Step 1a.3: `chunker.py`, fixed-size chunks with overlap (2026-10-12, not yet committed)

**Goal:** cut each document into pieces of `CHUNK_SIZE` characters (800), each starting
`CHUNK_SIZE - CHUNK_OVERLAP` (700) characters after the previous one. Deliberately naive
(D-006): it cuts through words and code. Phase 2 measures how much that hurts.

**Files:** `src/docpilot/chunker.py`, `tests/test_chunker.py`.

**Changed from the plan:** defaults read from `config` (no second copy of 800/100); new
"no text is lost" test (rebuild the input from the chunks); `itertools.pairwise` for
neighbour pairs (ruff B905).

**Real results** (36-character text `a..z0..9`, `chunk_size=10`, `overlap=3`, step 7):
| Chunk | Start | Text | Length |
|---|---|---|---|
| 0 | 0 | `abcdefghij` | 10 |
| 1 | 7 | `hijklmnopq` | 10 |
| 2 | 14 | `opqrstuvwx` | 10 |
| 3 | 21 | `vwxyz01234` | 10 |
| 4 | 28 | `23456789` | 8 |

`pytest tests/test_chunker.py -v`: 9 passed (5 tests + 1 test run with 4 bad settings).

| Prediction | Yours | Real |
|---|---|---|
| Number of chunks | 5 | 5 (correct) |
| Last chunk | `23456789`, 8 chars | `23456789`, 8 chars (correct) |
| Why 8 | "due to the overlap" | half right: overlap decides where it **starts** (28 = 4 x 7); the **text running out** decides the length (36 - 28 = 8) |
| Pad the last chunk to 800? | add dummy characters | no: see lessons |

**Lessons:**
1. Chunk length = `min(chunk_size, characters left after start)`. Overlap only moves the
   start. Homework: predict the last chunk for `fixed_size_chunks(t, "a.md", 10, 0)`,
   then run it.
2. Never pad text with dummy characters. The embedding turns *all* the text into meaning,
   so `"...0000000"` drags the vector toward "zeros"; the LLM also reads the padding and it
   costs tokens. Models accept any length up to 512 tokens. The tokenizer pads *inside* the
   model with `[PAD]` tokens and an attention mask tells the model to ignore them. Padding
   is the model's job, not ours.
3. The real last-chunk problem is the opposite: a **tiny tail**. At 800/100 the last chunk
   of a long document can be as short as 101 characters, and 100 of those are repeated
   from the previous chunk. Fixes (Phase 2 ideas): merge a short tail into the previous
   chunk, or chunk by headings/sentences.
4. `[10-10]`, `[0-0]` in test names come from `@pytest.mark.parametrize`: one test
   function, run once per settings pair.

**New concepts:** chunk, overlap, step, tail chunk, parametrized tests, attention mask.

---

## 17. Step 1a.4: `embedder.py` (2026-10-12, commit `8eff576`)

Loads BGE once (`lru_cache`), pinned with `revision=` (plan bug fixed). Chunks: no prefix,
batches of 32, normalised. Questions: BGE prefix added by hand, because the model's stored
`encode_query` prompt is empty (checked on sentence-transformers 6.1.0). 4 tests (shape 384,
length 1, empty list, model cached). **Learner run skipped**; the two prediction questions
(lru_cache speed; query vs document vector for the same word) are still open.

---

## 18. Step 1a.5: `vector_store.py`, Qdrant local mode (2026-10-12, not yet committed)

**Goal:** the only file that talks to Qdrant: fresh collection (384 dims, cosine), add
chunks as points (`uuid5` id + vector + payload), search top-k as plain dicts.
**New dependency:** `qdrant-client==1.19.1` (D-027). `client.search()` no longer exists;
`query_points` is the current API.

**Bug found by a test:** in local mode on disk, delete + create brought the old points
back (`assert 3 == 0`). Fix: delete all points with an empty filter, then fail if any
remain. Without it, Phase 2 re-ingests would mix old and new chunks.

**Real results** (3 fake chunks: `[1,0,0,0]`, `[0,1,0,0]`, `[0,0,1,0]`, query
`[0, 0.9, 0.1, 0]`, the same 3 chunks added twice):
| Prediction | Yours | Real |
|---|---|---|
| Order | chunk 1, then chunk 2 | `text 1 0.994`, `text 2 0.11`, `text 0 0.0` (correct) |
| Count after adding twice | 3, "because the collection is deleted and recreated" | 3 (correct number, wrong reason) |

`pytest tests/test_vector_store.py -v`: 5 passed in 1.58 s.

**Lessons:**
1. Cosine ignores length, only direction counts: 0.9 / sqrt(0.81 + 0.01) = 0.994. That is
   why the score is above 0.9 even though the query's value is 0.9.
2. Count stays 3 because of **upsert + deterministic ids**: the second add writes to the
   same 3 ids and overwrites them. `create_fresh_collection` ran only once, before both adds.
   With random `uuid4` ids the count would be 6, and every re-ingest would duplicate.
3. A score of 0.0 means "nothing in common" (no shared direction), not "wrong answer".
   Real BGE scores are rarely 0; Lab 1 saw 0.379 for an unrelated cat sentence.

---

## 19. Step 1a.6: `llm.py`, one client for free providers (2026-10-12, not yet committed)

**Goal:** send a system + user message to a free LLM and get the answer text. The provider
is a setting in `.env` (`LLM_PROVIDER`, `LLM_MODEL`); only the URL and key change.

**Free, no OpenAI account:** `openai` is a free open-source *client library*; requests go to
`https://api.groq.com/openai/v1` with the Groq key. `openai/gpt-oss-120b` is an open-weight
model that Groq hosts on its free plan (D-028). Your account's model list has no Llama 3.x.

**Plan bugs fixed:** empty answer silently returned `""` (reasoning models can use the
whole budget thinking) -> now raises; defaults frozen at import -> read at call time;
unknown provider -> clear `ValueError`.

**Real results:**
| Prediction | Yours | Real |
|---|---|---|
| Same question twice at temperature 0 | "not guaranteed identical" | identical this time (1 pair, 2.1 s for 2 calls) |
| Model not on the account | error, maybe 404; no silent switch | `NotFoundError: 404 ... model_not_found` |

`pytest tests/test_llm.py -v`: 5 passed in 0.93 s (fake client, no network).

**Lessons:**
1. Temperature 0 = always pick the most likely next token. Usually repeatable, but not a
   promise: server batching and GPU maths can still change a word now and then. One
   identical pair does not prove it; your first instinct was reasonable.
2. Reading the traceback bottom-up: `NotFoundError` (what), `404` (HTTP code: "no such
   thing"), `model_not_found` (Groq's reason). The library does not retry a 404; it only
   retries 429 (rate limit) and 5xx (server errors), because waiting will not fix a typo.
3. LLM text can hold invisible differences: "high‑performance" uses a non-breaking hyphen
   (U+2011), not "-". Evals that compare strings must normalise them first.

---

## 20. Step 1a.7: `rag.py`, the whole pipeline (2026-10-12, not yet committed)

**Goal:** question -> `embed_query` -> `search` top 4 -> numbered context -> `chat` ->
`{"answer", "sources"}`. Citation `[n]` always means `sources[n-1]`. Changed from the plan:
empty index returns NOT_FOUND without an LLM call. 4 tests with monkeypatched fakes.

**Demo** (3 handmade chunks in a temporary Qdrant: optional query param, path params
required, uvicorn; real BGE + real Groq `gpt-oss-120b`):
| | Q1 "make a query parameter optional?" | Q2 "deploy FastAPI to Kubernetes?" |
|---|---|---|
| Answer | `q: str \| None = None` ... `[1]` | `I could not find this in the documents.` |
| Sources | doc0 0.882, doc1 0.590, doc2 0.446 | doc2 0.604, doc1 0.442, doc0 0.421 |
| Your prediction | doc0, cites it (correct) | LLM adds its own facts (wrong); "source 3 related" (wrong) |

**Lessons:**
1. Vector search never says "nothing matched": it always returns the top k (here all 3).
   Q2's best score (0.604, the uvicorn chunk) beats Q1's second (0.590). A raw score alone
   cannot tell relevant from irrelevant. Ideas for later: score threshold, reranker (3.5).
2. Here the **LLM** did the abstaining, because the prompt told it to. One example is not
   proof; step 1d measures abstention on many questions.
3. "Cite every fact" was only half followed: one `[1]` at the end, not per fact. Citation
   quality is something the evals will measure, not assume.

---

## 21. Step 1a.8: the three scripts, DocPilot on real docs (2026-10-12, not yet committed)

**Goal:** turn the library code into something you can run end to end on real
documentation. This closes step 1a: after it, DocPilot answers from real FastAPI docs.

**Two pipelines (the shape of every real RAG system):**
```text
OFFLINE, once per change of docs or settings (slow: embeds every chunk)
  01_download_docs.py  ->  data/docs/fastapi/*.md
  02_ingest.py         ->  load -> chunk 800/100 -> embed -> fresh Qdrant collection

ONLINE, every question (fast: one embedding, one search, one LLM call)
  03_ask.py "question" ->  ask() -> answer + numbered sources with score and preview
```

**Files:** `scripts/01_download_docs.py`, `scripts/02_ingest.py`, `scripts/03_ask.py`;
decision D-029 (corpus).

**Corpus (D-029):** FastAPI tutorial pages `first-steps`, `path-params`, `query-params`,
`body`, **pinned to commit `d62354434b2e`** (licence MIT, all URLs checked 2026-10-12).

**Design choices, each with its reason:**
| Choice | Why |
|---|---|
| Pinned commit, not `master` | Docs edited upstream must not move our C0 number |
| `write_bytes`, not `write_text` | `write_text` on Windows turns `
` into `

`; chunks would differ from Linux CI |
| `urllib` (standard library) | No new dependency for four downloads |
| Ingest exits on an empty docs folder | The loader reports `[]`; the script decides it is fatal and says what to run |
| `client.close()` in `finally` | Releases the local Qdrant folder lock (D-003) even after a crash |
| `03_ask.py` prints source, chunk number, score, preview | You must **see** what was retrieved, not trust the answer |

**Noise kept on purpose:** `{* ../../docs_src/... *}` include markers (the code lives in
other files we did not download) and some HTML. Phase 2 (2.2, 2.3) removes it and
measures the gain.

**Run:**
```powershell
python scripts/01_download_docs.py
python scripts/02_ingest.py
python scripts/03_ask.py "How do I make a query parameter optional?"
python scripts/03_ask.py "How do I connect FastAPI to a PostgreSQL database?"
```

`03_ask.py` also prints **per-stage timings** (embed_query, search, llm, total) for that one
run. It is a cold start (new process, model loaded inside the first stage): one sample, not
a p50/p95. The real baseline L0 comes in step 1d (D-031).

**Real results:** n/a (learner run pending). Fill in: chunks per page, total chunks,
ingest time, top source and score for each question, answer or NOT_FOUND, stage timings.

**Interview line:** "I split indexing from querying, pinned the corpus to a commit and
wrote files byte-for-byte, so the same input gives the same chunks on every machine.
That is what makes my baseline number trustworthy."

---

## 22. Scope change v1.2 (2026-10-12): wider corpus + latency

**Corpus (D-030), agreed with the learner:**
| Group | What | Status |
|---|---|---|
| A. Technical docs | FastAPI now; Pydantic, Docker, Qdrant, LangChain, LangGraph, Redis in 2.8 | Phase 1 + 2.8 |
| B. Learning material | open-licence AI/ML/GenAI concepts (licence checked per source) | 2.8 |
| C. Interview prep | your own `docs/interview/*.md` and notes, open-licence Q&A | 2.8 |

- **Not** a "chat with any document" tool: no golden set is possible for "anything", and
  uploads are the main prompt-injection and copyright risk. Uploads = stretch 8.6, only
  after the Phase 6 guardrails gate.
- Material you add from other sources is welcome: open licence or your own = usable
  anywhere; anything else = `local_only` (laptop index only, never committed, never in the
  public demo).
- Phase 1 is unchanged, so C0 never moves. Phase 2 adds a `domain` tag (2.5), a Q&A-pair
  chunker for interview files (2.6), a corpus register with licences (2.8), at least 10
  golden questions per domain, and a per-domain score table (2.9). Phase 3.8 can filter by
  domain.

**Latency (D-031):** measured like accuracy, from Phase 1. `ask()` now returns
`timings_ms` per stage; step 1d adds `evals/run_latency.py` for the baseline **L0**
(p50/p95, warm, n, hardware named). Later phases charge every technique against L0.
Primer: `docs/teaching/primer_latency.md`. Interview: `phase_1_interview.md` Q15.

**Files changed:** PROJECT_DOCUMENTATION v1.2, decisions D-030/D-031, CLAUDE.md, Phase 1
part 2, Phase 2, 3 and 8 plans, architecture part 1, teaching index, primer_latency (new),
`rag.py` + `test_rag.py` + `03_ask.py` (timings).

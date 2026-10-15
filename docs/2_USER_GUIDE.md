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

**Real results (2026-10-12, run by the mentor at the learner's request, laptop CPU):**
| Page | Characters | Chunks |
|---|---|---|
| `body.md` | 6611 | 10 |
| `first-steps.md` | 14102 (14155 bytes: emoji take several bytes) | 21 |
| `path-params.md` | 9041 | 13 |
| `query-params.md` | 4596 | 7 |
| **Total** | | **51**, ingest 7.5 s |

Both questions are rows 1 and 2 of `docs/failure_log_phase1.md`: the optional-parameter
answer was right but showed code that is not in the docs; PostgreSQL gave `NOT_FOUND`
although search returned 4 chunks (top 0.705).

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

---

## 23. Step 1b: watch naive RAG fail (2026-10-12, not yet committed)

**Goal:** before any number exists, look at real failures with your own eyes. Like a
doctor who examines the patient before ordering lab tests: the tests (step 1d) only make
sense once you know what to look for.

**File:** `docs/failure_log_phase1.md`: 10 questions, one row each, filled in your own
words. Each row: prediction (before running), answer correct?, right chunk in the top 4
(with rank)?, what went wrong.

**Why 10 hand-picked questions and not a script yet?** A script tells you *how often*
retrieval fails; only reading chunks tells you *why*. The "why" decides which Phase 2/3
feature to build. Why not 50? Ten covers every question type once; more comes in 1c as a
golden dataset you can score automatically.

**Two traps on purpose:**
- **Ungrounded but "correct" answers.** An LLM knows FastAPI from its training data. If it
  states a fact that is in none of the 4 retrieved chunks, the answer did not come from
  our docs. In RAG that is a failure (faithfulness), even when the fact is true.
- **"Right page" is not "right chunk".** A chunk from the right page can still miss the
  passage. Use `--full` and read the chunk.

**Run (after the 1a.8 run):**
```powershell
python scripts/03_ask.py --full "Show me the code for a minimal FastAPI app."
```
One question per run; fill the row before running the next one.

**Real results (2026-10-12, 10 questions, see the log for every row):**
- Right chunk in the top 4 (at least partly): 8 of 8 answerable questions.
- Answers: 6 right, 2 partly (Q1 invented code "from the docs"; Q10 multi-hop, no "how"),
  1 wrong (Q7: only `{* ... *}` markers were indexed, so "show me the code" got
  `NOT_FOUND`). Both questions with no answer in the pages got `NOT_FOUND`.
- Scores do not separate good from bad: irrelevant top chunk 0.705 (Q2) vs correct 0.700
  (Q5). So "drop chunks below a score" is not a fix.
- Lesson: on 4 pages the **search** is fine; the **content of the chunks** (markers, HTML,
  mid-sentence cuts) and the **LLM's honesty** (Q1) are the problems. Phase 2 targets the
  first, Phase 3.9 measures the second.
- Cold single-run timings: embed_query about 2.0 to 2.2 s (includes loading the model),
  search under 2 ms, llm 0.9 to 1.6 s. Warm p50/p95 comes in 1d.

**Interview line:** "Before writing any eval, I ran 10 questions by hand and logged each
failure with the retrieved chunks. The most common cause was ___, which is why my first
Phase 2 fix was ___, and the eval showed ___." (Fill in the blanks with real results only.)

---

## 24. Step 1c: the golden dataset, an answer key (2026-10-12, not yet committed)

**Goal:** turn "it seems better" into a number. Like a teacher's answer sheet: without it,
marking an exam is an opinion.

**Files:** `evals/golden/dev.jsonl` (22 items), `evals/golden/test.jsonl` (10 items),
`evals/golden/README.md`, `evals/validate_golden.py`, `tests/test_validate_golden.py`;
decision D-032.

**Each item says:** the question, its type, should DocPilot answer it at all, a reference
answer, and the **evidence**: which page plus a short sentence copied exactly from it.

**Key ideas:**
| Idea | Why |
|---|---|
| Evidence = page + exact sentence, not chunk id (D-010) | chunk ids change when chunking changes; the page text does not, so one answer key serves every Phase 2 strategy |
| dev (22) and test (10) | dev is for trying things; test is the final exam, opened only at gates. Tuning on test is like reading the exam questions in advance |
| The 1b questions are all in dev | we already saw their answers; they cannot be a fair final exam |
| 5 unanswerable (16%), mostly near-misses | checks that DocPilot says "not found" even when the chunks look related |
| A validator with an **exact** match | one typo in a snippet turns a correct hit into a miss and lowers the score silently |

**Why not let an LLM write the questions?** It copies the page's own words, so paraphrase
and near-miss questions disappear and the scores look better than real users would get.
LLM-generated sets are a Phase 4 topic (RAGAS), and they still need a human check.

**Run:**
```powershell
python evals/validate_golden.py
```
**Real result (2026-10-12):** 32 items, dev 22 (3 unanswerable), test 10 (2 unanswerable),
OK. Full test suite: 39 passed.

**Interview line:** "My answer key labels evidence by document and a verbatim snippet, not
by chunk id, so the same 32 questions score every chunking strategy. A validator checks
every snippet character for character, and the test split is only run at gates."

---

## 25. Step 1d: the eval harness, scoring automatically (2026-10-13, not yet committed)

**Goal:** one command turns the answer key into numbers: the first real score **C0**,
the speed baseline **L0**, and abstention accuracy.

**Files (all in `evals/`):**
| File | Job | Analogy |
|---|---|---|
| `matching.py` | is this chunk a hit? (snippet inside, or at least 70% of it) | the marker reading one answer |
| `metrics.py` | Recall@k, strict recall, reciprocal rank, nDCG, percentile | the marking rules |
| `common.py` | load the golden split (only if valid), label results with date + commit, retry 429s | the exam office |
| `run_retrieval_eval.py` | search each question, score, save, print a table | marking the whole exam |
| `run_latency.py` | full `ask()` on every dev question after one warm-up: p50/p95 per stage | a stopwatch on every answer |
| `run_abstention_check.py` | did it say "not found" exactly when it should? | checking the trick questions |
| `ABLATION.md` | the scoreboard: one row per change | the league table |

Tests: `tests/test_metrics.py` (every expected number worked out on paper),
`tests/test_matching.py`. Decision D-033.

**Why these details matter:**
- **Fetch 10, give the LLM 4.** The eval asks for 10 chunks so one search reports @1, @3
  and @5; `ask()` is unchanged.
- **Warm-up first.** The first call loads the model (about 2 s in 1b). Users of a running
  service never pay that, so it is not mixed into L0.
- **Nearest-rank percentile.** p95 is always a time some request really took.
- **429 retries counted, not hidden.** The openai library retries silently; we switch that
  off and count, because waiting after a rate limit is real slow-tail time.
- **`+dirty` in the commit label.** Commit first, then run, so every number points to code
  that exists in git.
- **Unanswerable items are skipped by the retrieval eval** (no evidence to find) and
  scored by the abstention check instead.

**Run (commit first):**
```powershell
python -m evals.run_retrieval_eval --split dev --config-id C0
python -m evals.run_latency --split dev --config-id C0
python -m evals.run_abstention_check --split dev --config-id C0
```
The last two make one LLM call per question (23 and 22 calls); they are run by hand, never
in CI.

**Real results, retrieval (2026-10-14, learner run, commit `06891f1`, dev n=19):**
| Metric | C0 |
|---|---|
| Recall@1 | 0.526 (10 of 19 at rank 1) |
| Recall@3 / Recall@5 | 0.842 / 0.842 (16 of 19) |
| strict Recall@5 | 0.781 |
| MRR | 0.667 |
| nDCG@5 | 0.670 |
| search latency, warm | p50 1.3 ms, p95 2.2 ms |

Misses: q-017 (paraphrase, rank 6), q-018 (bullet list, rank 6), q-023 (Enum "allowed
values" vs "predefined values", not in top 10). Lesson: half the time the right chunk is
found but not first; when the question uses different words than the page, dense search
alone misses. Per-type rows have n = 1 to 5, too few to compare types.

**Real results, latency L0 (2026-10-14, learner run, commit `8295859`, warm, n=22,
laptop CPU, Groq `openai/gpt-oss-120b`):**
| Stage | p50 | p95 | max |
|---|---|---|---|
| embed_query | 15.8 ms | 85.4 ms | 102.9 ms |
| search | 1.0 ms | 1.9 ms | 2.4 ms |
| llm | 1060.4 ms | 1748.8 ms | 1858.6 ms |
| **total** | **1107.2 ms** | **1763.7 ms** | 1945.5 ms |
| wall incl. 429 waits | 5933.9 ms | 8208.5 ms | 8238.2 ms |

15 rate-limit retries (free tier). The LLM is about 96% of the time, so speeding up search
or embedding cannot help much; streaming (TTFT), a faster model, or caching can.

**Real results, abstention (2026-10-14, learner run, commit `b061d62`, dev n=22):**
accuracy **0.909**; answered although it should refuse **0/3**; refused although it
should answer **2/19** (q-007: the code is only an include marker; q-017: the right chunk
was rank 6, but the LLM sees only the top 4). Safe failures (refusing) rather than made-up
answers, and both are caused upstream: ingestion (2.3) and retrieval (3.x).

---

## 26. Step 1e: the mini API (2026-10-14, not yet committed)

**Goal:** the same `ask()` behind a web address, so any program (or a browser) can use it.
Like putting a counter in front of the kitchen: same cook, but now customers can order.

**Files:** `src/docpilot/api.py`, `tests/test_api.py`; decision D-034 (fastapi 0.143.1,
uvicorn 0.54.0, httpx 0.28.1).

| Piece | What it does | Why |
|---|---|---|
| `AskRequest` (Pydantic) | question must be 1 to 2000 characters | bad input gets a 422 before our code runs |
| `lifespan` | opens Qdrant and the LLM client **once** at startup | every request is then "warm" (L0: 16 ms embed vs about 2000 ms cold) |
| plain `def ask_endpoint` | FastAPI runs it in a thread pool | slow LLM calls do not freeze the server |
| `Source` model | returns source, chunk number, score; **not** the chunk text | small responses; text stays on the server |
| fake `ask` in tests | tests need no model, no key, no Qdrant | fast, free, runnable in CI |

**Run:**
```powershell
uvicorn docpilot.api:app --reload
```
Open `http://127.0.0.1:8000/docs`, click `POST /ask`, "Try it out", type a question,
"Execute". Stop with Ctrl + C **before** running `02_ingest.py` (one process per Qdrant
folder, D-003).

**Real results:** server boot check 2026-10-14: `/docs` 200, `/ask` listed. Live answer
through the API: n/a (learner's run).

---

## 27. Step 1f: CI, PR template, branch protection (2026-10-14, files built)

**Goal:** nothing reaches `main` without a pull request and green checks. Like a building
inspector: no inspection, no moving in.

**Files:** `.github/workflows/ci.yml`, `.github/pull_request_template.md`,
`scripts/check_file_lengths.py`; decision D-035.

**What CI runs on every PR:** install (CPU-only torch, to avoid GBs of GPU libraries) ->
`ruff check .` + `ruff format --check .` -> `pytest -q` (no key, no LLM) -> 500-line check.

**Problems found while preparing it (and fixed):** ruff tried to reformat code sketches in
`docs/`; one eval result file was 744 lines; VS Code's Pyrefly could not find `evals`.

**Public or private?** GitHub answered our private repo with "Upgrade to GitHub Pro or make
this repository public" (2026-10-14): free private repos cannot protect `main`. History
was scanned first: no secrets in 21 commits. **Your decision:** stay private until the
whole project is finished, then go public. Until then CI still runs on every pull request;
you follow the PR workflow by habit instead of by a locked door (D-035).

**Real results:** local CI simulation: 62 tests passed, ruff clean, length check OK.
First GitHub CI run (2026-10-15, draft PR #1, run 38682492687): **green** in 1 min 36 s on
Linux: CPU-only torch (196 MB), ruff clean, **62 tests passed in 12.4 s**, length check OK.
GitGuardian (an app on your account) also found no secrets. Branch protection: deferred to
project end.


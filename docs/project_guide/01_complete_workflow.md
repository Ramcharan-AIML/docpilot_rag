# DocPilot: The Complete Workflow, From Scratch to Now

Written 2026-10-23. Simple English. Every number comes from a real run on this laptop
(Windows 11, CPU only). Unknown = `n/a`. Decisions are named like D-061; they are in
`docs/decisions.md`, `docs/2_decisions.md` and `docs/3_decisions.md`.

Files in this folder:

| File | What it gives you |
|---|---|
| `01_complete_workflow.md` (this file) | Everything, step by step: how each part works and how they connect |
| `02_architecture.md` | The architecture diagrams, then the story behind them |
| `03_interview_story.md` | A 5-minute project story, challenges and fixes, numbers to memorise |

How to read this file: Part 1 is the big picture. Parts 2 to 9 follow the data, in the
order it moves. Part 10 is a map of every file. Part 11 lists what is NOT built.

---

# Part 1: The big picture

## 1.1 What DocPilot is

DocPilot is a **question-answering assistant for technical documents**. You ask a
question; it finds the right paragraphs in the documents and writes an answer that
**cites** them, like [1] and [2]. If the answer is not in the documents, it says
"I could not find this in the documents." instead of guessing.

It has two kinds of documents:

| Library | What is in it | Who chose it |
|---|---|---|
| **Main library** | 20 documents: FastAPI, Pydantic and Docker docs, the Chain-of-Thought paper (PDF), 3 Wikipedia articles, my own interview notes | Me, carefully (licences checked), and **measured** with a test set |
| **Chat files** | Any PDF, Markdown or text file a user drops into a chat | The user; each chat sees only its own files |

**Real-life example:** a librarian. The main library is the library's own books, checked
and catalogued. Chat files are the papers you bring to the desk: the librarian reads them
only for you.

## 1.2 The technique: RAG

**RAG = Retrieval-Augmented Generation.**

1. **Retrieval:** find the few paragraphs ("chunks") most related to the question.
2. **Augmented:** put those chunks into the prompt.
3. **Generation:** the LLM writes the answer from those chunks only, with citations.

**Why RAG and not "just ask the LLM"?** The LLM does not know my documents, and it may
invent things. RAG gives it the evidence and makes it show where each fact came from.

## 1.3 The three big flows

| Flow | When | In one line |
|---|---|---|
| **Indexing (offline)** | Once, when the main library changes | documents -> clean text -> chunks -> vectors -> Qdrant |
| **Answering (online)** | Every question | question -> guards -> search -> rerank -> LLM -> guards -> answer |
| **Evaluating (offline)** | After every change | fixed test questions -> scores -> compare -> keep or reject the change |

The third flow is what makes this project an **engineering** project and not a demo:
every choice was measured before it was kept.

## 1.4 The journey (phases)

| Phase | What I built | Key real number |
|---|---|---|
| 0 Foundations | Labs: embeddings, cosine similarity, keyword vs meaning search | - |
| 1 Baseline | Loader, chunker, embedder, Qdrant, LLM client, `ask()`, mini API, golden set, metrics | Abstention 0.91, end-to-end p50 1.1 s |
| 2 Chunking | Cleaner, includes, Docling (PDF/DOCX), metadata, 11 chunking configs, MLflow, CI eval gate | Winner FT-200: R@5 0.780 -> 0.805, MRR 0.650 -> 0.701 |
| 3 Retrieval | Qdrant in Docker, S3 (SeaweedFS), BM25, hybrid RRF, reranker, query transforms, LLM-judge eval | R@5 0.878, MRR 0.725 (dev); test top-1 0.35 -> 0.65 |
| 6 Guardrails | Input, context and output guards; 18-attack red team | Attacks that worked: 2/18 -> 0/18; false blocks 0/84 |
| UI | Streamlit first (D-060), then React chat app (D-061) | 43-page upload: 0.10 s to answer, ready in 18.9 s |
| 4, 5, 8 | Agents, multi-agent, stretch goals | **Dropped** for the deadline (D-058): future work |
| 7 | Production (Docker, Prometheus, Grafana) | Next |

---

# Part 2: The tools and models

| Job | Tool / model | Why this one | Why not the other |
|---|---|---|---|
| Meaning search (dense vectors) | `BAAI/bge-small-en-v1.5`, 384 numbers per text, pinned revision | Small, fast on CPU, strong for English retrieval | Bigger models: slower on CPU; the comparison script exists but was not run (deadline) |
| Keyword search (sparse vectors) | BM25 (`Qdrant/bm25` via FastEmbed, k1 1.2, b 0.75) | Finds exact words: error names, flags, function names | Dense search alone misses exact words |
| Vector database | Qdrant v1.19.1 in Docker | Dense + sparse + filters + fusion in one call | A plain list in Python: no filters, no scale |
| Fusion | Reciprocal Rank Fusion (RRF, k=60), inside Qdrant | Merges two rankings by position, not by score | Adding scores: dense and BM25 scores are on different scales |
| Reranker | `cross-encoder/ms-marco-MiniLM-L6-v2` (91 MB) on the top 20 | R@5 0.878 at about 0.5 s | `bge-reranker-base` (1.1 GB): R@5 0.854 and 13x slower (6.4 s) |
| Text tool | sentence-transformers 6.1.0 (on torch, CPU) | Loads BGE and the cross-encoder | - |
| LLM (answers) | `openai/gpt-oss-120b` on Groq (free tier) | Free, fast (LLM p50 about 1 s), good at following "cite or refuse" | Paid APIs (rule: free only) |
| LLM (judge in evals) | `qwen/qwen3.8-27b` on Groq | A different model family, so it does not grade its own style | Same model judging itself |
| PDF reading (main library) | Docling 2.140.0 (layout + table models, OCR off) | Tables come out as real tables | PyMuPDF: tables come out as jumbled numbers |
| PDF reading (chat uploads) | pypdfium2 (already installed with Docling) | 43 pages in 10.8 s in total vs 182 s with Docling | Docling: about 4 s per page, too slow for a chat |
| API | FastAPI + uvicorn | Typed, fast, automatic docs page | Flask: no built-in validation |
| Chat database | SQLite (built into Python) | One file, zero setup, enough for one user | Postgres: a server to run (Phase 7 upgrade) |
| Frontend | React 19 + Vite 8 (+ react-markdown) | Professional chat UI, streaming text | Streamlit: quick but looked like a demo (kept in `ui/`) |
| Object storage | SeaweedFS (S3 API) + boto3 | Same code works with Amazon S3 later | MinIO: archived project |
| Experiment tracking | MLflow 3.17.1 | Every eval run saved with its settings | A spreadsheet: no history, no link to code |
| CI | GitHub Actions + GitGuardian | Tests, lint, file length, eval gate on every pull request | - |

---

# Part 3: Indexing the main library (offline flow)

This builds the searchable library. It runs once, and again when documents change.

```text
01_download_docs.py      02_ingest.py (the whole chain below, one command)
  data/docs/  ->  load  ->  clean  ->  includes  ->  chunk  ->  metadata  ->  embed  ->  Qdrant
                (Docling                                 (FT-200)          (BGE + BM25)  docpilot_v1_ft200
                 for PDF/DOCX)
```

## Step 3.1: Download (`scripts/01_download_docs.py`)

Every source is listed in a **register** (`src/docpilot/ingestion/sources.py`): what it is,
its URL, its licence, the exact version (a Git commit or a Wikipedia revision), the date
the licence was checked, and whether it may leave this laptop (`public` or `local_only`).
The script downloads **exactly** those versions into `data/docs/<technology>/`.

**Why pin versions?** If FastAPI edits a page tomorrow, my test answers would point at text
that changed. Pinning makes every number reproducible (challenge 3 in the interview file).

## Step 3.2: Load (`ingestion/loader.py`, `ingestion/document_loader.py`)

- `.md` and `.txt`: read as they are.
- `.pdf` and `.docx`: converted to Markdown by **Docling**, which reads the page layout and
  tables. It is slow (the 43-page paper took 182 s), so the result is cached in
  `data/processed/converted/`, keyed by the file's sha256 and the Docling version.
- Documents are sorted by their path **string**, so Windows and Linux give the same order.

## Step 3.3: Clean (`ingestion/cleaner.py`)

Removes HTML noise from the downloaded docs (front matter, shortcodes, long table padding),
so chunks contain words, not markup.

## Step 3.4: Includes (`ingestion/includes.py`)

The FastAPI docs say "see this code file" with `{* ... *}` markers. The include resolver
puts the real code in place, so a chunk about query parameters contains the actual example.

## Step 3.5: Chunk (`ingestion/chunkers/`)

A **chunk** is a small piece of a document: the unit we search and cite.

**Real-life example:** cutting a book into index cards. Too big, and one card holds five
topics (search gets confused). Too small, and an answer is split over three cards.

I compared **11 chunking strategies** (fixed characters, fixed tokens, recursive, semantic,
parent-child, hierarchical, Q&A pairs, contextual...). The winner, **FT-200**, is simple:
200 model tokens per chunk, 25 tokens of overlap. Result: 453 chunks.
Dev R@1 0.537 -> 0.634, R@5 0.780 -> 0.805, MRR 0.650 -> 0.701.

## Step 3.6: Metadata (`ingestion/metadata.py`)

Every chunk gets labels (the Qdrant "payload"): source file, chunk number, domain,
technology, document type, version, **heading path** (for example
`Query Parameters > Optional parameters`), has_code, has_table, and a content hash.
The heading path is what the UI shows under each source.

## Step 3.7: Embed (`embedding/dense.py`, `embedding/sparse.py`)

Each chunk becomes two vectors:

| Vector | What it captures | Model |
|---|---|---|
| Dense (384 numbers) | Meaning: "make a parameter optional" ~ "default value None" | BGE-small |
| Sparse (word weights) | Exact words: `Query`, `422`, `--publish` | BM25 |

**Gotcha I caught:** BGE needs a special prefix on **questions only**
(`Represent this sentence for searching relevant passages: `). A library helper looked like
it added it, but this model's stored prompt is empty, so it silently did nothing. I add the
prefix by hand in `embed_query()`.

## Step 3.8: Store (`store/qdrant_store.py`)

`create_fresh_collection()` creates the collection `docpilot_v1_ft200` with two named
vectors (`dense`, cosine distance; `sparse`, with Qdrant's IDF modifier). Point ids are
`uuid5(source#chunk_number)`: the same chunk always gets the same id. The build settings
are saved as a **manifest** next to the collection, and every eval result records it.

## Step 3.9: Back up (`storage/object_store.py`, `store/snapshots.py`)

- Raw documents can be uploaded to the S3 bucket `docpilot-raw-docs` (SeaweedFS on the
  laptop), and restored on a fresh machine with `02_ingest.py --from-s3`.
- Qdrant **snapshots** (a full copy of a collection) go to the `docpilot-snapshots`
  bucket and can be restored: the restored index gave identical scores.

---

# Part 4: Measuring everything (the evaluation flow)

## 4.1 The golden set (`evals/golden/`)

65 questions written from the documents, each with **evidence** (the exact sentence that
answers it). Split into **dev** (used for choosing settings), **test** (used ONCE at the
end, never for choices) and a 7-question **CI** set. Some questions are deliberately
**unanswerable** ("How do I connect FastAPI to PostgreSQL?") to test refusals.
`evals/validate_golden.py` checks that every evidence sentence really exists in the docs.

## 4.2 Retrieval metrics (written by hand in `evals/metrics.py`)

| Metric | Simple meaning |
|---|---|
| Recall@k | Was the right chunk anywhere in the top k? |
| MRR | How high was the first right chunk? (1st = 1.0, 2nd = 0.5, 3rd = 0.33) |
| nDCG@5 | Like MRR, but gives credit for several right chunks |
| p50 / p95 latency | Typical and slow-case time, per stage |

## 4.3 Answer quality (`evals/run_generation_eval.py`)

A second LLM (Qwen, a different family) acts as a **judge**: it splits each answer into
claims and checks each claim against the chunks (**faithfulness**), compares with my
reference answer (**correctness**) and rates **relevancy**. Result on 10 answers:
faithfulness 1.0, 0 made-up claims, correctness 1.0; 5 of 5 correct refusals. About 20%
of judged items go to `evals/spot_checks/` for a human to agree or disagree.

## 4.4 The ablation table and MLflow

Every run saves a JSON file in `evals/results/` with the git commit (plus `+dirty` if code
was uncommitted) and is logged in **MLflow**. `evals/ABLATION.md` is the table of every
configuration: what changed, what it scored, what it cost in time.

## 4.5 The CI eval gate (`scripts/ci_gate.py`, `.github/workflows/ci.yml`)

On every pull request, GitHub Actions builds a tiny index from fixture pages and runs an
18-question exam. If Recall@5 or MRR drops below the saved baseline, the pull request
gets a red cross. Proof it works: an injected chunking bug dropped MRR 0.87 -> 0.50 and
the gate failed the build.

## 4.6 What the measurements decided

| Experiment | Result | Decision |
|---|---|---|
| 11 chunking strategies | FT-200 best | Kept |
| BM25 alone | R@5 0.805, same as dense but on DIFFERENT questions | Use both (hybrid) |
| Hybrid RRF | R@5 0.829 | Kept |
| Reranker MiniLM vs bge-base | MiniLM better AND 13x faster | MiniLM kept |
| 4 query transforms (multi-query, HyDE, step-back, decomposition) | All R@5 0.878 = no gain, +0.9 to 2.7 s | None kept |
| Final pipeline on the unseen test split (n=17) | top-1 0.353 -> 0.647, MRR 0.608 -> 0.765 | The real headline |

---

# Part 5: Answering one question (`/ask`, no memory)

This is the core pipeline. The chat app (Part 6) wraps the same pieces.

```text
question
  1 input guard ............ blocked?  -> "Sorry, I can't help with that..."  (no search, no LLM)
  2 embed the question ..... BGE (with the query prefix) + BM25
  3 hybrid search .......... Qdrant: top 50 dense + top 50 BM25 -> RRF -> top 20
  4 rerank ................. MiniLM cross-encoder reads question + each chunk -> best 4
  5 build the prompt ....... 4 chunks in <document id="N"> boxes + guarded system prompt
  6 LLM .................... gpt-oss-120b on Groq writes the answer with [1] [2]
  7 output guard ........... no valid citation? -> "I could not find this in the documents."
  answer + sources + status + time per stage
```

| Step | File | Real time (p50, this laptop) |
|---|---|---|
| Input guard | `guardrails/input_guard.py` | 0.014 ms |
| Embed question | `embedding/dense.py`, `embedding/sparse.py` | about 30-75 ms |
| Hybrid search | `store/qdrant_store.py` `search_hybrid()` | 12.3 ms |
| Rerank 20 | `retrieval/reranker.py` | 485 ms (895 ms on a busier day) |
| LLM | `llm/client.py` | 990 ms |
| Output guard | `guardrails/output_guard.py` | 0.028-0.042 ms |
| End-to-end | `rag.py` `ask()` | one sample 2.7 s; p50 n/a until measured in Phase 7 |

**Why rerank?** Search compares the question and each chunk SEPARATELY (fast, but rough).
The cross-encoder reads them TOGETHER (slow, but accurate), so we use it only on the top 20.
**Real-life example:** a recruiter first skims 50 CVs by keywords, then interviews 20 people.

**Why only 4 chunks to the LLM?** Fewer, better chunks keep the prompt short (faster, fewer
tokens on the free tier) and give the LLM less room to wander.

`retrieval/pipeline.py` `retrieve()` is the **one front door** for steps 2-4: the app, the
API and every eval call the same function, so the app runs exactly what was measured.

---

# Part 6: The chat app: how React and FastAPI work together

## 6.1 Two programs, one conversation

| Program | Language | Where | Job |
|---|---|---|---|
| React app | JavaScript | `web/src/` | Draws the screen, sends requests, shows streamed text |
| FastAPI server | Python | `src/docpilot/` | Everything else: guards, memory, search, LLM, storage |

**Rule:** the React app has **no RAG logic**. It cannot skip a guard, because it never
touches the documents or the LLM. **Real-life example:** a restaurant's dining room and
kitchen. Guests (React) order through the waiter (the API); they never cook.

## 6.2 How the browser reaches the API

| Mode | Command | Address | How /api reaches Python |
|---|---|---|---|
| Development | `npm run dev` (in `web/`) + `uvicorn docpilot.api:app` | http://127.0.0.1:5173 | Vite **proxies** every `/api/...` request to port 8000 (`web/vite.config.js`) |
| Production | `npm run build` once, then `uvicorn docpilot.api:app` | http://127.0.0.1:8000 | FastAPI serves the built files from `web/dist/` AND the API: one origin, no CORS setup |

## 6.3 The API endpoints (`src/docpilot/chat_api.py`, under `/api`)

| Method + path | What it does | Answer |
|---|---|---|
| `POST /api/chats` | New chat | `{id, title: "New chat", ...}` |
| `GET /api/chats` | Sidebar list, newest activity first | list of chats |
| `GET /api/chats/{id}` | Open a chat | chat + all messages + all files |
| `PATCH /api/chats/{id}` | Rename | the chat |
| `DELETE /api/chats/{id}` | Delete chat, its messages, files on disk and vectors | `{deleted}` |
| `POST /api/chats/{id}/files` | Upload a file | **202** at once, status `processing` |
| `GET /api/chats/{id}/files` | File chips (the UI polls this) | list of files with status |
| `DELETE /api/chats/{id}/files/{file_id}` | Remove one file and its vectors | `{deleted}` |
| `POST /api/chats/{id}/messages` | Ask | a **stream** of events (Server-Sent Events) |

Plus `POST /ask` (one question, no memory, main library: scripts and evals), `GET /health`
and `GET /docs` (FastAPI's automatic API page).

## 6.4 The React side (`web/src/`)

| File | Job |
|---|---|
| `main.jsx` | Starts React inside `index.html` |
| `App.jsx` | Holds the state (chats, active chat, messages, files, theme) and all actions |
| `api.js` | Every HTTP call; reads the answer stream |
| `components/Sidebar.jsx` | New chat, chat list, rename, delete, light/dark switch |
| `components/Message.jsx` | One message: Markdown, citation badges, source cards, timings |
| `components/Composer.jsx` | Text box, attach button, file chips, "search in" switch, Send/Stop |
| `components/Icons.jsx` | Inline SVG icons |
| `styles.css` | Colour tokens (light default, dark switch), layout, phone width |

## 6.5 One message, end to end (what happens when you press Enter)

1. **React** (`App.jsx` `send()`): shows your message at once, plus an empty assistant
   message with "Searching your documents". If there is no chat yet, it creates one
   first (`POST /api/chats`).
2. **React** (`api.js` `streamMessage()`): `POST /api/chats/{id}/messages` with
   `{question, library}` (`library` = auto / files / main).
3. **FastAPI** (`chat_api.py` `message()`): checks the chat exists, then returns a
   `StreamingResponse` that runs `chat/service.py` `run_turn()`.
4. **Server** (`run_turn`): reads the chat's history from SQLite, saves your message, runs
   the input guard, the memory step, retrieval, the streamed LLM call and the output guard
   (Part 8 has the details), and saves the answer.
5. **Server -> browser**, as Server-Sent Events, one line each:
   ```text
   data: {"type": "sources", "sources": [...], "question": "<standalone question>"}
   data: {"type": "token", "text": "Docker "}            <- many of these
   data: {"type": "done", "answer": "...", "status": "ok", "sources": [...], "timings": {...}}
   ```
6. **React**: `sources` changes the label to "Writing the answer"; each `token` is added to
   the text (with a blinking cursor); `done` **replaces** the text with the final, guarded
   answer and shows source cards and the time per stage.
7. **React** refreshes the sidebar (new title from your first question, new order).

**Real measurement:** through the Vite proxy, 310 tokens arrived one by one between 2.63 s
and 3.28 s; the stream is not held back until the end.

---

# Part 7: Uploads: where the files go

## 7.1 The path of one uploaded file

```text
Browser: drop "handbook.pdf" on the window (or click the paper clip)
  |
  | POST /api/chats/{chat}/files   (multipart form)
  v
chat_api.upload()
  1 save_upload() ...... safe name, real PDF? (%PDF), <= 50 MB, <= 500 pages
  2 disk ............... data/uploads/<chat id>/handbook.pdf
  3 SQLite ............. files table: status "processing"
  4 jobs.submit() ...... queue for the background worker
  5 reply 202 ........... the chip appears at once (0.10 s for 43 pages)
  |
  v  (background thread, chat/jobs.py)
ingest_file()
  read text (pypdfium2, "# Page N" before each page)
  clean -> 200-token chunks -> metadata -> BGE + BM25 vectors
  Qdrant collection "docpilot_uploads", every point labelled chat_id = <chat id>
  SQLite: status "ready", chunks, seconds    (or "failed" + a safe message)
  |
  v
React polls GET /api/chats/{chat}/files every 1.5 s -> spinner turns into a green tick
```

## 7.2 Where everything is stored (the full storage map)

| What | Where | Format | In git? |
|---|---|---|---|
| Main library documents | `data/docs/<technology>/` | .md, .pdf, .docx | No (re-downloaded by script) |
| Docling conversions | `data/processed/converted/` | Markdown + meta JSON | No (cache) |
| Main library vectors | Qdrant collection `docpilot_v1_ft200` (Docker named volume) | points: 2 vectors + payload | No |
| Uploaded files (raw) | `data/uploads/<chat id>/<file name>` | the original file | No (gitignored) |
| Uploaded chunks + vectors | Qdrant collection `docpilot_uploads`, payload `chat_id` | points | No |
| Chats, messages, file status | `data/app.db` (SQLite) | 3 tables | No |
| Raw docs backup, index snapshots | SeaweedFS buckets `docpilot-raw-docs`, `docpilot-snapshots` | S3 objects | No |
| Eval results | `evals/results/*.json` + MLflow | JSON | Yes (results) |
| LLM caches for evals | `evals/cache/*.json` | JSON | Yes (re-runs are free) |
| Code, tests, docs | the repository | - | Yes |

**Uploads are NOT copied to S3 / SeaweedFS today.** They live on this laptop only. That
fits their licence status: we do not know a user file's licence, so it is `local_only`
(`sources.UPLOADS`).

## 7.3 Why each piece

| Choice | Why | Cost |
|---|---|---|
| Separate collection for uploads | The measured main library (and its scores) never changes | Two collections to manage |
| `chat_id` on every uploaded chunk + a Qdrant filter | A chat searches only its own files (like a NotebookLM notebook) | None noticeable |
| Fast reader (pypdfium2) for uploads | 43 pages: 10.8 s vs 182 s | Tables become plain lines |
| `# Page N` headings | Each chunk knows its page, so sources say "Page 3" | - |
| One background worker thread | Embedding already uses all CPU cores | A job in progress is lost if the API restarts |
| Re-upload deletes old chunks first | A shorter new version must not keep old extra chunks | One delete call |
| Delete chat -> delete rows, folder and vectors | Nothing is left behind | - |

---

# Part 8: Memory and context management (what exists, honestly)

## 8.1 Two different words

| Word | Meaning |
|---|---|
| **Memory** | The app remembers what was said earlier in THIS chat |
| **Context management** | Deciding what goes into the LLM's prompt, so it stays small, relevant and safe |

**Yes, both are in the project now (D-061)**, in a simple, deliberate form. Here is exactly
what happens.

## 8.2 Where the history lives

- The **server** is the single source of truth: every message is saved in SQLite
  (`messages` table) by `chat/service.py`.
- The **React app does not send the history**. It sends only the new question. The
  server reads the history itself, so a browser cannot fake or bloat it.
- When you open an old chat, React loads it with `GET /api/chats/{id}`. A page reload
  loses nothing.

## 8.3 What goes into each LLM call (the context, exactly)

| LLM call | When | What is in its prompt | Size limit |
|---|---|---|---|
| **Condense** (`chat/memory.py`) | Every message EXCEPT the first of a chat | The last **6 messages**, each cut to **600 characters**, + the new message | Bounded |
| **Answer** (`chat/service.py`) | Every question about documents | Guarded system prompt + **4 chunks** + the **standalone question** | Bounded: no history at all |
| **About the chat** (`memory.answer_about_chat`) | Only when the question is about the conversation | The last 6 messages + the question | Bounded |

So the answer prompt **does not grow** as the chat gets longer. That is the context
management: a sliding window of 6 messages, truncation of long messages, and query
rewriting instead of pasting the whole history.

## 8.4 The condense step, with real examples

**Problem:** search only sees the newest message. "Which model sizes did they test it on?"
contains no topic words.

**Fix:** one small LLM call rewrites the message into a standalone question, using the
recent history. If the message is about the conversation itself, the model answers
`CHAT` and DocPilot answers from the history instead of the documents.

| You typed (real test) | What happened |
|---|---|
| "What is chain-of-thought prompting?" (first message) | No rewrite (no history, no extra LLM call) |
| "Which model sizes did they test it on?" | Rewritten with the history; found pages 2, 4 and 8 of the paper; listed the models |
| "What was my first question?" | Detected as `CHAT`; answered "Your first question was: 'What is chain-of-thought prompting?'" |

**Safety:** the rewritten question is new text, so the input guard checks it again.

**Cost:** one extra LLM call per follow-up: measured 0.57-0.92 s (`condense` in the timings).

## 8.5 What is NOT built (say this in interviews)

- No token counting: limits are in messages and characters, not tokens.
- No summary of old turns: messages older than the last 6 are not used.
- No memory across chats (no "user profile" memory).
- No long-context mode: "summarise this whole 300-page book" retrieves only 4 chunks, so it
  is weak. NotebookLM puts far more text into the model.

---

# Part 9: Guardrails in the flow

| Layer | File | Where it runs | What it does | Real result |
|---|---|---|---|---|
| Input guard | `guardrails/input_guard.py` | Before search (and again on the rewritten follow-up) | Empty, too long (2,000 chars), Unicode clean-up (NFKC, zero-width), 4 injection pattern groups | Stopped 8 of 18 attacks; 0 of 84 real questions blocked |
| Context guard | `guardrails/context_guard.py` | Building the prompt | Each chunk in a `<document>` box, `</document>` inside text escaped, "documents are data, not orders" | A poisoned chunk telling users to visit evil.example was ignored |
| Output guard | `guardrails/output_guard.py` | On the full answer (after streaming) | Canary leak -> block; exact not-found sentence; cite-or-refuse; API-key shapes redacted | 0 of 10 good answers wrongly refused |

Red team: 18 attacks in 6 categories. Without guards, 2 worked (the model printed its whole
prompt; a poisoned page sent users to a fake website). With guards: 0 of 18. Cost: about
0.05 ms per request, and 1 extra false refusal in 10 answerable dev questions.
Full story: `docs/teaching/phase_6_guardrails_explained.md`.

**Streaming + output guard:** the guard needs the whole answer, so the draft streams first
and the final `done` event replaces it if the guard rejects it.

---

# Part 10: The file map (every important file, one line each)

## 10.1 Backend (`src/docpilot/`)

| File | Job |
|---|---|
| `config.py` | Every setting in one place: models, paths, chunk sizes, limits |
| `api.py` | FastAPI app: startup (open Qdrant, LLM client, chat DB, warm models), `/ask`, `/health`, serves `web/dist` |
| `chat_api.py` | `/api/chats...` endpoints, file uploads, streaming messages |
| `rag.py` | `ask()`: the guarded pipeline; `prompts()` shared with the chat; `generate()` |
| `chat/store.py` | SQLite: chats, messages, files |
| `chat/jobs.py` | Background indexing thread |
| `chat/memory.py` | Condense (follow-up rewrite) and answers about the chat |
| `chat/service.py` | One chat turn: guards -> memory -> retrieval -> stream -> guard -> save |
| `retrieval/pipeline.py` | `retrieve()`: the one front door (hybrid + rerank, optional chat filter) |
| `retrieval/fusion.py` | Hand-written RRF (kept to prove Qdrant's matches) |
| `retrieval/hybrid.py` | Manual hybrid and multi-query search (experiments) |
| `retrieval/reranker.py` | Cross-encoder reranking |
| `retrieval/query_transforms.py` | HyDE, multi-query, step-back, decomposition (measured, not used) |
| `embedding/dense.py` | BGE embeddings (query prefix added by hand) |
| `embedding/sparse.py` | BM25 sparse vectors |
| `store/qdrant_store.py` | The only file that talks to Qdrant: create, add, search, filter, delete |
| `store/snapshots.py` | Back up / restore a collection to S3 |
| `storage/object_store.py` | S3 calls (SeaweedFS now, Amazon S3 later) |
| `llm/client.py` | One OpenAI-compatible client for free providers; `chat()` and `chat_stream()` |
| `guardrails/*.py` | Input, context and output guards |
| `ingestion/loader.py`, `document_loader.py` | Read files; Docling for PDF/DOCX |
| `ingestion/cleaner.py`, `includes.py`, `blocks.py` | Clean text, resolve code includes, parse blocks |
| `ingestion/chunkers/*.py` | The 9 chunking strategies (fixed tokens is the app's) |
| `ingestion/metadata.py` | Payload labels incl. heading path |
| `ingestion/sources.py` | Licence register (+ `UPLOADS`, local_only) |
| `ingestion/manifest.py` | Saves each collection's build settings |
| `ingestion/uploads.py` | Chat uploads: checks, fast reader, ingest with `chat_id` |

## 10.2 Scripts, evals, frontend, tests

| Folder | What is in it |
|---|---|
| `scripts/` | `01_download_docs.py`, `02_ingest.py`, `03_ask.py`, `04_sync_docs.py`, `ci_gate.py`, `check_file_lengths.py`, snapshots, chunking matrix |
| `evals/` | Golden set, metrics, retrieval / latency / abstention / generation / red-team runners, MLflow logging, ABLATION.md |
| `web/` | The React app (Part 6) |
| `ui/` | The first UI (Streamlit, D-060), kept; its question box still works, its upload panel does not |
| `tests/` | 305 tests: guards, chunkers, store, API, chat store, chat service, uploads, UI client |
| `docker-compose.yml` | Qdrant v1.19.1, SeaweedFS 4.48, MLflow 3.17.1 |
| `.github/workflows/ci.yml` | Lint, tests, file-length rule, eval gate |

---

# Part 11: What is not built (never present these as done)

| Not built | Why | Plan |
|---|---|---|
| Agents (LangGraph), multi-agent, human-in-the-loop, MCP | Deadline (D-058) | Future work |
| NeMo Guardrails, Llama Guard, Presidio (personal data) | Deadline; light plain-Python guards first | Compare on the same 18 attacks |
| RAGAS | Own judge already measures the same things | Compare later |
| Docker image of the app, Prometheus + Grafana | Next step (Phase 7, small) | Starting now |
| AWS (S3, Terraform, EC2) | Cut for the deadline (D-061) | Future work |
| Long-context summaries, OCR, token-based memory | Scope | Future work |
| End-to-end p50 of the final pipeline | Not measured yet | Prometheus + a small load test |

---

# Part 12: Run it yourself

```powershell
.venv\Scripts\Activate.ps1
docker compose up -d                       # Qdrant, SeaweedFS, MLflow
uvicorn docpilot.api:app                   # API (+ built React app) on http://127.0.0.1:8000
cd web ; npm run dev                       # optional: UI with live reload on http://127.0.0.1:5173
python -m pytest -q                        # 305 tests
```

Read next: `02_architecture.md` (the diagrams), then `03_interview_story.md`.

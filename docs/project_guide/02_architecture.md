# DocPilot Architecture

Written 2026-10-23. Simple English. The diagrams use Mermaid: GitHub shows them as
pictures (in VS Code, install a Mermaid preview extension). Section 1 is plain text, so it
reads well anywhere. The story under the diagrams explains every box.

---

## 1. One-page overview (plain text)

```text
 ┌──────────────────────────── BROWSER ─────────────────────────────┐
 │  React app (web/)                                                  │
 │  Sidebar: chats    Conversation: streamed answers [1][2]           │
 │  Composer: question box, file chips, "search in" switch            │
 └───────────────┬──────────────────────────────────────▲────────────┘
                 │ HTTP JSON  /api/...                   │ Server-Sent Events (streamed words)
 ┌───────────────▼──────────────────────────────────────┴────────────┐
 │  FastAPI server (src/docpilot/)                                     │
 │                                                                     │
 │  API layer        api.py (/ask, /health, serves web/dist)           │
 │                   chat_api.py (/api/chats, files, messages)         │
 │                                                                     │
 │  Chat layer       chat/service.py  one turn, end to end             │
 │                   chat/memory.py   follow-up rewrite ("condense")   │
 │                   chat/jobs.py     background indexing              │
 │                   chat/store.py    SQLite: chats, messages, files   │
 │                                                                     │
 │  Safety layer     guardrails/ input -> context -> output            │
 │                                                                     │
 │  RAG core         rag.py  ask(), prompts()                          │
 │                   retrieval/pipeline.py  retrieve(): hybrid+rerank  │
 │                   embedding/ BGE (dense) + BM25 (sparse)            │
 │                   retrieval/reranker.py  MiniLM cross-encoder       │
 │                   llm/client.py  Groq, OpenAI-compatible, streaming │
 │                                                                     │
 │  Data layer       store/qdrant_store.py   storage/object_store.py   │
 │                   ingestion/ (offline: load, clean, chunk, tag)     │
 └──────┬──────────────────┬──────────────────┬───────────────┬───────┘
        │                  │                  │               │
   ┌────▼─────┐     ┌──────▼──────┐    ┌──────▼─────┐   ┌─────▼──────┐
   │ Qdrant   │     │ SQLite      │    │ Local disk │   │ Groq LLM   │
   │ 2 colls  │     │ data/app.db │    │ data/...   │   │ gpt-oss-   │
   │ (Docker) │     │             │    │ uploads    │   │ 120b       │
   └──────────┘     └─────────────┘    └────────────┘   └────────────┘
   SeaweedFS (S3 API, Docker): raw-docs + snapshots    MLflow (Docker): eval runs
```

---

## 2. System context: who talks to whom

```mermaid
flowchart LR
    user([User in a browser])
    subgraph laptop[This laptop]
        web[React app<br/>web/]
        api[FastAPI server<br/>src/docpilot/]
        qdrant[(Qdrant<br/>vectors)]
        sqlite[(SQLite<br/>data/app.db)]
        disk[(Local disk<br/>data/docs, data/uploads)]
        s3[(SeaweedFS<br/>S3 buckets)]
        mlflow[(MLflow<br/>eval runs)]
    end
    groq[[Groq API<br/>gpt-oss-120b, qwen judge]]
    gh[[GitHub Actions<br/>CI + eval gate]]

    user --> web
    web -- "/api JSON + SSE stream" --> api
    api --> qdrant
    api --> sqlite
    api --> disk
    api -- "HTTPS, free tier" --> groq
    api -. "backups, snapshots" .-> s3
    api -. "eval scripts only" .-> mlflow
    gh -. "on every pull request" .-> api
```

**Story.** The user only ever sees the React app. Every real decision happens in the
FastAPI server. The server keeps vectors in Qdrant, chats in SQLite, files on the local
disk, and calls Groq for the LLM. SeaweedFS (an S3-compatible store) holds backups, and
MLflow holds evaluation runs; neither is on the path of a normal question. GitHub Actions
tests the code on every pull request, including an eval gate that fails a pull request when
retrieval quality drops.

---

## 3. Backend layers (inside the FastAPI server)

```mermaid
flowchart TB
    subgraph L1[API layer]
        api_py[api.py<br/>/ask, /health, static web/dist]
        chat_api[chat_api.py<br/>/api/chats, files, messages]
    end
    subgraph L2[Chat layer]
        service[chat/service.py<br/>run_turn]
        memory[chat/memory.py<br/>condense, about-chat]
        jobs[chat/jobs.py<br/>1 background worker]
        store[chat/store.py<br/>SQLite]
    end
    subgraph L3[Safety layer]
        ig[guardrails/input_guard.py]
        cg[guardrails/context_guard.py]
        og[guardrails/output_guard.py]
    end
    subgraph L4[RAG core]
        rag[rag.py<br/>ask, prompts]
        pipe[retrieval/pipeline.py<br/>retrieve]
        emb[embedding/dense.py + sparse.py<br/>BGE + BM25]
        rr[retrieval/reranker.py<br/>MiniLM]
        llm[llm/client.py<br/>chat, chat_stream]
    end
    subgraph L5[Data layer]
        qs[store/qdrant_store.py]
        ing[ingestion/*<br/>loader, cleaner, chunkers, metadata, uploads]
        obj[storage/object_store.py<br/>store/snapshots.py]
    end

    api_py --> rag
    chat_api --> service
    chat_api --> jobs
    chat_api --> store
    service --> store
    service --> memory
    service --> ig
    service --> og
    service --> pipe
    service --> llm
    rag --> ig
    rag --> cg
    rag --> og
    rag --> pipe
    rag --> llm
    memory --> llm
    jobs --> ing
    pipe --> emb
    pipe --> qs
    pipe --> rr
    ing --> emb
    ing --> qs
    obj --> qs
```

**Story.** Each layer only talks to the layer below it.

- **API layer:** turns HTTP into function calls and back. It validates input with Pydantic
  (too long or empty -> 422 before any of our code runs) and never decides anything about
  RAG.
- **Chat layer:** everything a conversation needs: saved history (SQLite), the follow-up
  rewrite, background indexing, and `run_turn()`, which runs one turn end to end.
- **Safety layer:** three guards, plain Python, about 0.05 ms in total. They wrap every
  path that reaches the LLM: `/ask`, the chat, and the follow-up rewrite.
- **RAG core:** `retrieve()` is the **one front door** for search, used by the app, the API
  and every eval, so the app runs exactly what was measured. `prompts()` is the one
  prompt builder, shared by `ask()` and the streaming chat.
- **Data layer:** `qdrant_store.py` is the only file that talks to Qdrant. Swapping the
  vector database would change one file.

---

## 4. The question pipeline (one chat turn)

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant R as React (App.jsx)
    participant A as chat_api.py
    participant S as chat/service.py
    participant DB as SQLite
    participant M as chat/memory.py
    participant Q as Qdrant
    participant X as Reranker (MiniLM)
    participant L as Groq LLM

    U->>R: types a question, presses Enter
    R->>A: POST /api/chats/{id}/messages {question, library}
    A->>S: run_turn() (streamed)
    S->>DB: read history, save user message
    S->>S: input guard (0.014 ms)
    alt chat has earlier messages
        S->>M: condense(question, last 6 messages)
        M->>L: rewrite as a standalone question (or "CHAT")
        L-->>M: standalone question
    end
    S->>S: input guard again on the rewrite
    S->>Q: hybrid search (dense + BM25, RRF), filter chat_id if files
    Q-->>S: top 20 chunks
    S->>X: rerank 20 -> best 4
    S-->>R: event "sources"
    S->>L: guarded prompt: 4 chunks in boxes + question (stream)
    loop while the LLM writes
        L-->>S: next words
        S-->>R: event "token"
    end
    S->>S: output guard on the full answer
    S->>DB: save the answer, sources, timings
    S-->>R: event "done" (final answer may replace the draft)
    R-->>U: answer with [1] badges, source cards, time per stage
```

**Story.** The browser sends only the new question; the server reads the history itself.
The input guard runs first, so an attack costs no search and no LLM call. If the chat
already has messages, one small LLM call rewrites the question so pronouns like "it" make
sense to search (and detects questions about the chat itself, which are answered from the
history). Hybrid search finds 20 candidates, the reranker keeps the best 4, and the LLM
streams its answer word by word. Because the output guard needs the whole answer, it runs
at the end; if it rejects the draft, the final event replaces it. Real numbers: condense
0.6-0.9 s, rerank about 0.85 s, first words from the LLM after 0.8-1.1 s, whole turn
2.3-3.0 s.

---

## 5. The upload pipeline (files per chat)

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant R as React
    participant A as chat_api.py
    participant D as data/uploads/<chat>/
    participant DB as SQLite (files)
    participant W as chat/jobs.py worker
    participant Q as Qdrant docpilot_uploads

    U->>R: drops handbook.pdf
    R->>A: POST /api/chats/{id}/files
    A->>A: checks: name, %PDF, 50 MB, 500 pages
    A->>D: save the file
    A->>DB: row, status "processing"
    A->>W: submit job
    A-->>R: 202 Accepted (0.10 s)
    R-->>U: chip with spinner
    W->>W: pypdfium2 text, "# Page N", clean, 200-token chunks
    W->>W: BGE + BM25 vectors
    W->>Q: upsert points with chat_id
    W->>DB: status "ready", chunks, seconds
    loop every 1.5 s while processing
        R->>A: GET /api/chats/{id}/files
        A-->>R: status
    end
    R-->>U: green tick (43 pages: ready after 18.9 s)
```

**Story.** ChatGPT and NotebookLM also index uploads; they feel instant because the work
happens in the background. DocPilot does the same: the request only checks and saves the
file and returns at once. A single worker thread does the slow part. Each chunk carries the
chat's id, and search in that chat uses a Qdrant filter on it, so other chats never see the
file. For speed, uploads use the pypdfium2 text reader (43 pages: 10.8 s) instead of
Docling (182 s); the price is that tables become plain lines.

---

## 6. The offline pipelines (indexing and evaluation)

```mermaid
flowchart LR
    subgraph IDX[Indexing the main library: scripts/02_ingest.py]
        dl[01_download_docs.py<br/>pinned versions] --> load[load<br/>Docling for PDF/DOCX]
        load --> clean[clean + includes]
        clean --> chunk[chunk FT-200<br/>200 tokens, overlap 25]
        chunk --> meta[metadata<br/>heading path, flags]
        meta --> embed[BGE + BM25]
        embed --> col[(Qdrant<br/>docpilot_v1_ft200<br/>453 chunks)]
    end
    subgraph EV[Evaluation]
        gold[golden set<br/>65 questions] --> runs[run_retrieval_eval<br/>run_generation_eval<br/>run_redteam]
        col --> runs
        runs --> res[evals/results JSON<br/>+ MLflow]
        res --> abl[ABLATION.md<br/>keep or reject]
        gate[CI eval gate<br/>fixture index, 18 questions] --> pr{pull request<br/>green or red}
    end
```

**Story.** Indexing turns documents into searchable chunks, once. Evaluation turns every
idea into a number: chunking (11 configurations), hybrid search, two rerankers, four query
transforms, guardrails. Only changes that won on the dev questions were kept; the test
questions were used once, at the end. Every result is tied to a git commit and logged in
MLflow, and the CI gate protects retrieval quality on every pull request.

---

## 7. Where data lives

```mermaid
flowchart TB
    subgraph Q[Qdrant, Docker named volume]
        c1[docpilot_v1_ft200<br/>main library, measured]
        c2[docpilot_uploads<br/>every point has chat_id]
    end
    subgraph SQL[SQLite data/app.db]
        t1[chats]
        t2[messages]
        t3[files]
    end
    subgraph DISK[Local disk, gitignored]
        d1[data/docs<br/>main library sources]
        d2[data/uploads/chat id<br/>uploaded files]
        d3[data/processed<br/>Docling cache]
    end
    subgraph S3[SeaweedFS, S3 API]
        b1[docpilot-raw-docs]
        b2[docpilot-snapshots]
    end
    t3 -. "source name" .- c2
    d2 -. "read by the worker" .- c2
    d1 -. "backup" .- b1
    c1 -. "snapshot" .- b2
```

**Story.** Each kind of data has one home. Vectors live in Qdrant, conversations in SQLite,
original files on disk. The main library and its index can be rebuilt from S3 on a new
machine. Uploaded files are `local_only` (their licence is unknown), so they are not copied
to S3. Deleting a chat removes its rows, its upload folder and its vectors.

---

## 8. Design principles behind the architecture

| Principle | Where you see it | Why |
|---|---|---|
| Measure before you keep | evals/, ABLATION.md, CI gate | Every choice in the pipeline has a number behind it |
| One front door | `retrieve()`, `prompts()` | The app and the evals run the same code |
| The UI has no logic | React only calls `/api` | Guards cannot be skipped; the UI can be replaced |
| Layers talk downwards | API -> chat -> safety -> RAG -> data | Easy to test each layer with fakes (305 tests) |
| One file per outside system | `qdrant_store.py`, `object_store.py`, `llm/client.py` | Swap Qdrant, S3 or the LLM provider in one place |
| Raw first, then the library | Hand-written RRF and metrics before Qdrant fusion | I understand what the library does |
| Free and pinned | Groq free tier, local models with pinned revisions, exact package versions | Reproducible numbers, zero cost |
| Background for slow work | `chat/jobs.py` | The user never waits for indexing |

---

## 9. Limits of this architecture (honest)

| Limit | Effect | Next step |
|---|---|---|
| One API process, one worker thread | Fine for one user; many users would queue | Phase 7: more workers, a job queue |
| SQLite | One file; not for many servers | Postgres |
| Uploads on local disk | Lost if the laptop is lost | S3 with per-user access |
| A job in progress is lost on restart | Its chip stays "processing" | A persistent queue |
| 4 chunks per answer | Whole-book summaries are weak | Map-reduce summaries or a long-context model |
| No monitoring yet | End-to-end p50 under load is n/a | Prometheus + Grafana (next) |

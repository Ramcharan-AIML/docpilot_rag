# DocPilot RAG

A question-answering assistant for technical documentation, built step by step as a
learning project. It answers **only from the indexed documents**, cites its sources, says
"I could not find this" when the documents do not contain the answer, and **proves its
quality with measured numbers**. Everything runs on free tools (local models, free LLM tiers).

**Documents indexed (v1):** FastAPI, Pydantic and Docker docs, three Wikipedia articles
(RAG, word embeddings, IR evaluation measures), the Chain-of-Thought paper (PDF), and the author's own
interview notes: 20 documents, 453 chunks. The public demo leaves the personal notes out
(413 chunks) and shows its library on the welcome screen.

**Live demo:** https://docpilot.duckdns.org (AWS EC2 t3.small in Sydney, built with
Terraform; Caddy + Let's Encrypt HTTPS; free-plan credits, so the link moves to Oracle
Cloud before 2027-04-24).

---

## Where the project is now (2026-10-22)

| Phase | What it is about | Status |
|---|---|---|
| 0 | Foundations: environment, embedding labs | done (tag `phase-0`) |
| 1 | Simple RAG baseline, golden question set, eval harness, mini API | done (tag `phase-1`) |
| 2 | Better ingestion: cleaning, code and tables kept whole, 6 chunking strategies, MLflow, CI eval gate | done (tag `phase-2`) |
| 3 | Better retrieval: Docker, keyword search, hybrid search, reranking, ... | **in progress** (steps 3.1 to 3.6, 3.9, 3.10 done) |
| 4 | Agentic RAG with LangGraph | dropped for the deadline (future work) |
| 5 | Multi-agent, tools, MCP server, human review | dropped for the deadline (future work) |
| 6 | Guardrails and security tests | done (light version, D-059) |
| 7 | Production: Docker, Prometheus + Grafana, CI/CD, AWS S3 with Terraform | next (core) |
| 8 | Stretch goals (GraphRAG-lite, DSPy, ColBERT, ...) | dropped (future work) |

The full story in simple English: [docs/USER_GUIDE.md](docs/USER_GUIDE.md) and its parts 2 to 4.

---

## What is done, with real numbers

All numbers come from real runs. Dev set = 41 answerable questions (1 question = 0.024).
Full table: [evals/ABLATION.md](evals/ABLATION.md).

**Phase 1: baseline**
- Golden question set with evidence and a validator (65 questions in v1).
- Metrics written by hand: Recall@k, MRR, nDCG, abstention accuracy, p50/p95 latency.
- Abstention accuracy 0.91 with zero invented answers (golden v0); end-to-end p50 1.1 s.

**Phase 2: ingestion and chunking**
- HTML cleaner, include resolver, block parser, metadata, Docling for PDF and DOCX.
- 11 chunking configurations compared. Winner FT-200 (200 tokens, overlap 25):
  dev R@1 0.537 -> 0.634, R@5 0.780 -> 0.805, MRR 0.650 -> 0.701.
- Every run logged in MLflow. A CI eval gate fails a pull request if retrieval quality drops.

**Phase 3 so far: retrieval**
| Step | What | Result |
|---|---|---|
| 3.1 | Qdrant in Docker | same scores as local; search p50 7.6 ms |
| 3.1b | S3-style storage (SeaweedFS + boto3), MLflow server, index snapshots | docs and index round-trip with identical scores |
| 3.2 | Keyword search (BM25 sparse vectors) | R@5 0.805, same as meaning search, but on different questions |
| 3.3 | Hybrid search with hand-written RRF | R@5 0.829, R@3 0.805 (dense: 0.805, 0.732) |
| 3.4 | Same hybrid inside Qdrant (one call) | same results, search 12.3 ms vs 24.8 ms |
| 3.5 | Reranker (cross-encoder) on the top 20 | MiniLM: **R@5 0.878, MRR 0.725**, +0.5 s per question (big bge-reranker-base: R@5 0.854 at +6.4 s) |
| 3.6 | Query transforms (multi-query, HyDE, step-back, decomposition) | none helped: all R@5 0.878 = no transform, +0.9 to 2.7 s each, so none kept |
| 3.9 | Generation eval with an LLM judge (Qwen) | 10 judged answers: faithfulness 1.0, 0 made-up facts, correctness 1.0; refusals 5/5 |
| 3.10 | One retrieval front door, used by the app | `ask()` and the API now run hybrid + reranker |

---

## What comes next (plan for submission, D-058)

**Phase 6: guardrails (light), done (D-059).** Plain-Python input guard, untrusted-context
boxes, cite-or-refuse output guard with a canary; red team: attacks that worked 2/18 ->
0/18, false blocks 0/84.

**Phase 7: production (core).**
- Docker image for the API (models baked in), full Docker Compose stack.
- Prometheus + Grafana: live latency per stage (embed, search, rerank, LLM), request
  count, refusal rate; a small load test to see latency under several users.
- GitHub Actions CD: build the image and push it to GitHub Container Registry (CI tests
  and the eval gate already run on every pull request).
- AWS: account safety (MFA, budget alarm), S3 buckets with Terraform, the app switched
  from local SeaweedFS to real S3; one EC2 server if time allows.

**Future work (not built, on purpose):** agents with LangGraph, multi-agent and
human-in-the-loop review, MCP server, metadata filters, embedding-model comparison (built,
not run), Redis cache, Postgres, LiteLLM fallbacks, Kubernetes (k3s / EKS), Oracle move,
stretch goals (GraphRAG, DSPy, ColBERT).

---

## Run it locally

Windows PowerShell, Python 3.12+, Docker Desktop running.

```powershell
python -m venv .venv ; .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt ; pip install -e .
copy .env.example .env                 # then fill in your free LLM key and local settings
docker compose up -d                   # Qdrant, SeaweedFS, MLflow
python scripts/01_download_docs.py     # fetch the documents (pinned versions)
python scripts/make_notes_docx.py      # build the interview-notes DOCX
python scripts/02_ingest.py            # chunk, embed, index (see config.INGEST_ARGS)
python scripts/03_ask.py "How do I set a max length on a query parameter?"
python -m evals.run_retrieval_eval --split dev --retriever hybrid-server   # score retrieval
python -m pytest -q                    # tests
```

**Web app (React, D-061):** chats with memory, files per chat, streaming answers.

```powershell
cd web ; npm install ; npm run build ; cd ..   # once (needs Node.js 22)
uvicorn docpilot.api:app                       # then open http://127.0.0.1:8000
```

While changing the UI: run `npm run dev` in `web/` and open http://127.0.0.1:5173
(it passes /api to the API on port 8000). Upload PDF / Markdown / text files (up to 500
pages); they are indexed in the background and only that chat searches them.

---

## Stack (all free)

Python, sentence-transformers (`BAAI/bge-small-en-v1.5`), FastEmbed BM25, Qdrant, cross-encoder
rerankers, Groq / Gemini / OpenRouter free models, FastAPI, MLflow, SeaweedFS + boto3,
Docker Compose, GitHub Actions.

## Documentation map

[docs/README.md](docs/README.md) lists every document: project documentation (the source of
truth), architecture, implementation plans, teaching notes, decisions, progress, interview notes.

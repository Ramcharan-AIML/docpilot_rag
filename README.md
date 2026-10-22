# DocPilot RAG

A question-answering assistant for technical documentation, built step by step as a
learning project. It answers **only from the indexed documents**, cites its sources, says
"I could not find this" when the documents do not contain the answer, and **proves its
quality with measured numbers**. Everything runs on free tools (local models, free LLM tiers).

**Documents indexed (v1):** FastAPI, Pydantic and Docker docs, three Wikipedia articles
(RAG, word embeddings, IR evaluation measures), the Chain-of-Thought paper (PDF), and the author's own
interview notes: 20 documents, 453 chunks.

---

## Where the project is now (2026-10-22)

| Phase | What it is about | Status |
|---|---|---|
| 0 | Foundations: environment, embedding labs | done (tag `phase-0`) |
| 1 | Simple RAG baseline, golden question set, eval harness, mini API | done (tag `phase-1`) |
| 2 | Better ingestion: cleaning, code and tables kept whole, 6 chunking strategies, MLflow, CI eval gate | done (tag `phase-2`) |
| 3 | Better retrieval: Docker, keyword search, hybrid search, reranking, ... | **in progress** (steps 3.1 to 3.5 done) |
| 4 | Agentic RAG with LangGraph | next |
| 5 | Multi-agent, tools, MCP server, human review | planned |
| 6 | Guardrails and security tests | planned |
| 7 | Production: hardened API, cache, monitoring, Docker, CI/CD, AWS with Terraform, k3s | planned |
| 8 | Stretch goals (GraphRAG-lite, DSPy, ColBERT, ...) | optional |

Day-by-day detail: [docs/progress.md](docs/progress.md). The full story in simple English:
[docs/USER_GUIDE.md](docs/USER_GUIDE.md) and its parts 2 to 4.

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

---

## What comes next (to the end)

**Phase 3 (remaining)**
- 3.6 Query transforms: multi-query, HyDE, step-back, decomposition (LLM calls cached).
- 3.7 Embedding model comparison (bge-small vs bge-base, bge-m3, nomic, e5).
- 3.8 Metadata filters (technology, domain).
- 3.9 Generation eval: faithfulness, answer relevancy, correctness, with an LLM judge
  and hand spot-checks.
- 3.10 One retrieval front door: `retrieve(question, settings)` with the winning defaults.
- Gate: chunking re-check through the final pipeline, interview notes, PR, tag `phase-3`.

**Phase 4: agentic RAG.** A hand-made agent loop first, then LangGraph (state, nodes,
conditional edges, limits); RAGAS / DeepEval compared with our own metrics; agent vs
no-agent row.

**Phase 5: multi-agent and tools.** Calculator, SQL over extracted tables, web search;
supervisor + specialist agents; human-in-the-loop review with saved checkpoints; an MCP server.

**Phase 6: guardrails.** Red-team question set; input and output guards in plain Python
first; poisoned-document test; PII masking (Presidio); compare NeMo Guardrails / Llama Guard.

**Phase 7: production.** Async FastAPI with streaming, API keys, Postgres, Redis cache and
rate limits, LLM fallback (LiteLLM), tracing, Prometheus + Grafana, RAG monitoring,
multi-arch Docker images, CI/CD, AWS free plan via Terraform (EC2, S3, ECR), HTTPS, k3s,
an EKS exercise, load test; later a move to Oracle Cloud Always Free.

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

---

## Stack (all free)

Python, sentence-transformers (`BAAI/bge-small-en-v1.5`), FastEmbed BM25, Qdrant, cross-encoder
rerankers, Groq / Gemini / OpenRouter free models, FastAPI, MLflow, SeaweedFS + boto3,
Docker Compose, GitHub Actions. Every choice and its "why not X?" is in
[docs/decisions.md](docs/decisions.md) and [docs/2_decisions.md](docs/2_decisions.md).

## Documentation map

[docs/README.md](docs/README.md) lists every document: project documentation (the source of
truth), architecture, implementation plans, teaching notes, decisions, progress, interview notes.

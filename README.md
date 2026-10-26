<div align="center">

# DocPilot

**Grounded answers from technical documentation, with citations and honest refusals.**

[![Live demo](https://img.shields.io/badge/live%20demo-docpilot.duckdns.org-2ea44f?style=for-the-badge)](https://docpilot.duckdns.org)

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?logo=react&logoColor=61DAFB)
![Qdrant](https://img.shields.io/badge/Qdrant-DC244C)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?logo=terraform&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-232F3E?logo=amazonwebservices&logoColor=white)
![Tests](https://img.shields.io/badge/tests-340%20passing-brightgreen)

[Live demo](https://docpilot.duckdns.org) · [How it works](#how-it-works) · [Results](#results) · [Getting started](#getting-started) · [Deployment](#deployment)

</div>

---

## Overview

DocPilot is a Retrieval-Augmented Generation (RAG) assistant for technical documentation.
Ask a question, and DocPilot finds the most relevant passages, has a language model answer
**only from those passages**, and links every statement to its source. When the documents
don't contain the answer, it says *"I could not find this in the documents."* instead of
guessing.

The built-in library covers **FastAPI, Pydantic, Docker**, the **Chain-of-Thought**
research paper, and Wikipedia articles on RAG, word embeddings and retrieval evaluation.
Users can also attach their own PDF, Markdown or text files to a conversation.

Every design choice was measured on a fixed set of evaluation questions before it was
kept.

## Key features

| | |
|---|---|
| **Cited answers** | every claim references a numbered source chunk; uncited answers are rejected |
| **Honest refusals** | answers only from retrieved text, and declines when the answer is not there |
| **Hybrid retrieval** | dense semantic search + BM25 keyword search, fused with Reciprocal Rank Fusion |
| **Reranking** | a cross-encoder reorders the top candidates for precision |
| **Guardrails** | input, context and output checks against prompt injection and prompt leaks |
| **Conversations** | chat history with follow-up question rewriting and streamed responses |
| **Your own files** | per-conversation uploads, indexed in the background, searched only in that chat |
| **Measured quality** | golden question set, retrieval metrics, LLM-as-judge, red-team suite, CI quality gate |
| **Production-ready** | Docker, CI/CD, infrastructure as code on AWS, automatic HTTPS |

---

## How it works

### Query pipeline

```text
                    ┌──────────────────────────────────────────────┐
  User question ──► │ Input guard   injection, length, hidden chars │
                    └──────────────────────┬───────────────────────┘
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ Condense      follow-up → standalone question │
                    └──────────────────────┬───────────────────────┘
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ Hybrid search (Qdrant)                        │
                    │   dense:  bge-small-en-v1.5  (meaning)        │
                    │   sparse: BM25               (keywords)       │
                    │   fusion: Reciprocal Rank Fusion → top 20     │
                    └──────────────────────┬───────────────────────┘
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ Rerank        MiniLM cross-encoder → top 4    │
                    └──────────────────────┬───────────────────────┘
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ Generate      LLM answers from 4 delimited    │
                    │               sources, cites [1]..[4], streams│
                    └──────────────────────┬───────────────────────┘
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ Output guard  cite-or-refuse, leak check,     │
                    │               secret redaction                │
                    └──────────────────────┬───────────────────────┘
                                           ▼
                                  Answer + sources
```

### Ingestion pipeline

```text
Pinned source documents ─► clean HTML ─► resolve code includes ─► keep code/tables whole
   ─► 200-token chunks (25 overlap) ─► dense + sparse vectors ─► Qdrant (+ build manifest)
```

### System architecture

```text
                         https://docpilot.duckdns.org
                                     │
 ┌───────────────────────── AWS EC2 (Docker Compose) ─────────────────────────┐
 │                                                                            │
 │   Caddy ──────────► FastAPI application ──────────► Qdrant                 │
 │   HTTPS, Let's      REST + streaming API            vector database        │
 │   Encrypt certs     React web app                   (library + uploads)    │
 │                     embedding + reranker models                            │
 │                     SQLite (chats, files)                                  │
 └────────────────────────────────────────────────────────────────────────────┘
        ▲                         ▲                         ▲
   container image          API key (encrypted)       index snapshot
   GitHub Container         AWS SSM Parameter         private S3 bucket
   Registry                 Store
```

---

## Results

All results come from recorded runs. Each configuration changes **one** thing and is
scored on the same questions. Full table with result files: [`evals/ABLATION.md`](evals/ABLATION.md).

### Retrieval: development set (41 answerable questions)

| Configuration | Recall@5 | MRR |
|---|:---:|:---:|
| Baseline: fixed 800-character chunks, dense search | 0.780 | 0.650 |
| Token-based chunks (200 / 25) on cleaned text | 0.805 | 0.701 |
| + Hybrid search (dense + BM25, RRF) | 0.829 | 0.687 |
| **+ Cross-encoder reranking (top 20)** | **0.878** | **0.725** |
| + Query transforms (multi-query, HyDE, step-back, decomposition) | 0.878 | no gain, excluded |

### Retrieval: held-out test set (17 questions, evaluated once)

| Metric | Baseline | Final pipeline |
|---|:---:|:---:|
| Recall@1 | 0.353 | **0.647** |
| Recall@5 | 0.941 | **0.941** |
| MRR | 0.608 | **0.765** |
| nDCG@5 | 0.674 | **0.790** |

### Reranker comparison (CPU)

| Reranker | Size | Recall@5 | Added latency |
|---|:---:|:---:|:---:|
| `BAAI/bge-reranker-base` | 1.1 GB | 0.854 | +6.4 s |
| **`cross-encoder/ms-marco-MiniLM-L6-v2`** | **91 MB** | **0.878** | **+0.5 s** |

### Generation and safety

| Check | Result |
|---|---|
| Faithfulness (LLM-as-judge, 10 answers) | 1.0, no unsupported claims |
| Correct refusals on unanswerable questions | 5 / 5 |
| Red-team attacks succeeding (18 attacks, 6 categories) | 2 → **0** |
| False blocks on legitimate questions | **0 / 84** |

### Operations

| Metric | Value |
|---|---|
| Hybrid search latency (p50) | 12.3 ms |
| Container image | 1.86 GB (models included) |
| Image build (cold / cached) | 3 min 33 s / 29 s |
| Server boot to serving traffic | 319 s, fully automated |

---

## Tech stack

| Area | Technology |
|---|---|
| Language | Python 3.13 |
| Backend | FastAPI, Pydantic, Uvicorn |
| Frontend | React, Vite |
| Dense embeddings | `BAAI/bge-small-en-v1.5` (sentence-transformers), 384 dimensions |
| Sparse embeddings | BM25 via FastEmbed |
| Reranker | `cross-encoder/ms-marco-MiniLM-L6-v2` |
| Vector database | Qdrant 1.19 (named dense + sparse vectors, server-side fusion) |
| LLM | `openai/gpt-oss-120b` on Groq, through an OpenAI-compatible client (also supports OpenRouter, Gemini, Ollama) |
| Document parsing | Docling (curated library), pypdfium2 (fast uploads) |
| Application data | SQLite |
| Experiment tracking | MLflow |
| Containers | Docker (multi-stage build), Docker Compose |
| Reverse proxy / TLS | Caddy with Let's Encrypt |
| CI/CD | GitHub Actions, GitHub Container Registry, GitGuardian |
| Cloud | AWS EC2, S3, IAM, Systems Manager (Parameter Store, Session Manager) |
| Infrastructure as code | Terraform |
| Quality | pytest, ruff, actionlint, shellcheck |

---

## Getting started

### Prerequisites

- Python 3.12+
- Docker Desktop (or Docker Engine with Compose)
- Node.js 22 (to build the web app)
- A free API key from [Groq](https://console.groq.com) (or OpenRouter / Gemini)

### Installation

```bash
git clone https://github.com/Ramcharan-AIML/docpilot_rag.git
cd docpilot_rag

python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1

pip install -r requirements-dev.txt
pip install -e .

cp .env.example .env                 # Windows: copy .env.example .env
# set GROQ_API_KEY and LLM_MODEL in .env
```

### Build the index

```bash
docker compose up -d                 # Qdrant, SeaweedFS (S3-compatible storage), MLflow
python scripts/01_download_docs.py   # fetch the source documents at pinned versions
python scripts/02_ingest.py --clean --includes --strategy fixed_tokens \
    --size 200 --overlap 25 --collection docpilot_v1_ft200
```

### Ask a question

```bash
python scripts/03_ask.py "How do I set a max length on a query parameter?"
```

### Run the web app

```bash
cd web && npm install && npm run build && cd ..
uvicorn docpilot.api:app             # open http://127.0.0.1:8000
```

For frontend development, run `npm run dev` in `web/` and open http://127.0.0.1:5173.

### Configuration

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `groq`, `openrouter`, `gemini` or `ollama` |
| `LLM_MODEL` | model name for the chosen provider |
| `GROQ_API_KEY` | API key (or the key for your provider) |
| `QDRANT_URL` | Qdrant server URL; empty = embedded local mode |
| `PUBLIC_MODE` | `1` enables rate limits, upload caps and cleanup for public hosting |

---

## Evaluation

```bash
python -m pytest -q                                                        # unit tests
python -m evals.run_retrieval_eval --split dev --retriever hybrid-server   # retrieval metrics
```

- **Golden set:** 65 hand-written questions with evidence passages, including
  unanswerable questions, split into a development set (for experiments) and a test set
  (evaluated only at milestones).
- **Metrics:** Recall@k, MRR, nDCG@5, abstention accuracy and per-stage latency,
  implemented in [`evals/metrics.py`](evals/metrics.py).
- **LLM-as-judge:** a separate model grades faithfulness and correctness.
- **Red team:** [`evals/redteam/attacks.jsonl`](evals/redteam/attacks.jsonl) covers direct and
  indirect prompt injection, prompt extraction, jailbreaks, encoded attacks and off-topic
  requests.
- **CI quality gate:** every pull request rebuilds a small index and fails if retrieval
  quality drops below the stored baseline.

---

## API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | liveness: the process is running |
| `GET` | `/ready` | readiness: models, vector database, library and LLM key are available |
| `POST` | `/ask` | single question, returns the answer with sources |
| `GET` | `/api/library` | documents in the built-in library |
| `POST` `GET` | `/api/chats` | create or list conversations |
| `GET` `PATCH` `DELETE` | `/api/chats/{id}` | read, rename or delete a conversation |
| `POST` `GET` | `/api/chats/{id}/files` | upload a file (indexed asynchronously) or list files |
| `POST` | `/api/chats/{id}/messages` | send a message; the response is streamed as events |

---

## Project structure

```text
docpilot_rag/
├── src/docpilot/
│   ├── api.py                 FastAPI app, health and readiness, web app serving
│   ├── chat_api.py            conversation, upload and streaming endpoints
│   ├── rag.py                 end-to-end question answering pipeline
│   ├── config.py              central configuration
│   ├── limits.py              rate limiting and concurrency control
│   ├── chat/                  storage, conversation memory, background jobs, cleanup
│   ├── ingestion/             loading, cleaning, chunking strategies, uploads
│   ├── embedding/             dense and sparse encoders
│   ├── retrieval/             hybrid search, rank fusion, reranking, query transforms
│   ├── guardrails/            input, context and output guards
│   ├── llm/                   provider-agnostic LLM client
│   └── store/                 Qdrant access, snapshots, index seeding
├── web/                       React frontend
├── evals/                     golden sets, metrics, evaluation runners, red-team suite
├── scripts/                   download, ingest, query and maintenance scripts
├── tests/                     test suite
├── infra/aws/                 Terraform configuration and first-boot script
├── deploy/                    Caddy configuration
├── .github/workflows/         CI (tests, eval gate) and CD (image build)
├── Dockerfile
├── docker-compose.yml         local development services
└── docker-compose.prod.yml    production stack
```

---

## Deployment

The production system runs on AWS and is fully reproducible from this repository.

```text
 Pull request ──► CI: tests · retrieval eval gate · secret scan
       │
   merge to main
       ▼
 CD: build image ──► push to GHCR as sha-<commit>
       │
 terraform apply (infra/aws)
       ▼
 EC2 · Elastic IP · security group (80/443) · IAM role · S3 · SSM
       │
 first boot (cloud-init)
       ▼
 install Docker ─► read secret from SSM ─► start stack ─► restore index from S3
       │
       ▼
 Caddy obtains a Let's Encrypt certificate ─► live over HTTPS
```

**Security**
- No SSH: the server has no port 22; administration uses AWS Session Manager.
- No long-lived cloud credentials: Terraform runs in AWS CloudShell, and the server uses
  an IAM role scoped to one parameter path and one bucket.
- Secrets live in SSM Parameter Store, never in the image, the repository or Terraform state.
- Containers run as a non-root user; only the reverse proxy exposes ports.

**Run the production stack locally**

```bash
docker build -t docpilot:dev .
APP_IMAGE=docpilot:dev docker compose -f docker-compose.prod.yml up -d   # https://localhost
```

**Release and rollback:** the server pins an immutable `sha-<commit>` image tag.
Rolling back means redeploying the previous tag.

---

## Design decisions

- **Measure, then decide.** Every component earned its place on the evaluation set.
  Query transforms added 1–3 s per question without improving recall, so they are not
  used.
- **Smaller can be better.** The 91 MB MiniLM reranker outperformed a 1.1 GB alternative
  and runs 13× faster on CPU.
- **Hybrid over single-mode search.** Dense and keyword search each reached Recall@5
  0.805, but on different questions; combining them recovers both.
- **Capacity from data.** Rate limits are derived from measured tokens per answer against
  the provider's per-minute token budget.
- **Same code path everywhere.** The application, the API and the evaluations share one
  retrieval function, so measured quality is the quality users get.

## Limitations

- Single-server deployment; restarts cause brief downtime.
- Throughput is bounded by the free LLM tier (about 3 answers per minute site-wide).
- Evaluation sets are small; differences of one or two questions are treated as ties.

## Roadmap

- [ ] Prometheus and Grafana dashboards: per-stage latency, refusals, guard events
- [ ] Automated deployments with GitHub OIDC
- [ ] LLM provider fallback
- [ ] Agentic retrieval (relevance grading and query retry), benchmarked against the current pipeline
- [ ] Larger evaluation set

---

## Acknowledgements

The built-in library uses openly licensed content:
[FastAPI](https://github.com/fastapi/fastapi) (MIT),
[Pydantic](https://github.com/pydantic/pydantic) (MIT),
[Docker documentation](https://github.com/docker/docs) (Apache-2.0),
Wei et al., *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models*
(CC BY 4.0), and Wikipedia (CC BY-SA 4.0).

## Author

**Ramcharan Yachamaneni** · [GitHub](https://github.com/Ramcharan-AIML)

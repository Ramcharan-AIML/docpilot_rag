# Resume Entry: DocPilot

Copy-ready text for your resume and LinkedIn. Updated 2026-10-21 (Phase 2 done, Phase 3
step 3.1 done). **Rule:** every number comes from a real run in `evals/ABLATION.md` or the
decision log. A tool you list must be one you can explain and show; interviewers ask about
every word.

Two versions:
- **Version 1 (send now):** what's built and measured today, plus one honest "in progress"
  line. That line still puts the full stack's keywords in front of the ATS.
- **Version 2 (full project):** the finished project from start to deployment. Use it once
  those phases exist, and fill every `[X]` only from a real run. Never send a `[X]`.

---

## Version 1: send now (true on 2026-10-21)

**DocPilot: Evaluation-Driven RAG Assistant for Technical Docs, AI/ML Papers and Interview Prep**
*Python, RAG, FastAPI, Pydantic, Qdrant, Hugging Face (BGE embeddings), Docling (PDF/DOCX),
LLM APIs (Groq, OpenAI-compatible), MLflow, Docker, Docker Compose, GitHub Actions (CI), pytest*

- Built an end-to-end **Retrieval-Augmented Generation (RAG)** assistant over 20 documents
  in 3 domains (FastAPI/Pydantic/Docker docs, AI/ML papers and articles, interview notes),
  including **PDF and Word** files parsed with **Docling**, served via a **FastAPI**
  endpoint that returns cited answers and refuses when the answer isn't in the documents.
- Designed an **LLM evaluation harness from scratch**: a 65-question golden dataset
  (dev/test split, 3 domains, unanswerable "near-miss" questions) labelled with verbatim
  evidence and an automatic validator. Implemented **Recall@k, MRR, nDCG, abstention
  accuracy and per-stage p50/p95 latency** by hand. Baseline: **0.91 abstention accuracy
  with zero fabricated answers**, and showed the LLM is ~96% of response time.
- Ran an **11-configuration chunking ablation** (fixed, token-based, recursive, semantic,
  parent-child, hierarchical, Q&A-pair) tracked in **MLflow**, all within the embedding
  model's 512-token limit. The chosen strategy raised **Recall@1 from 0.54 to 0.63** on dev
  (0.35 to 0.47 on the held-out test set) with no loss in recall and the smallest LLM context.
- Used error analysis to fix **data-quality issues** (HTML noise, unresolved code
  includes, PDF table padding, captions split from tables), and found data cleaning
  mattered more than the choice of chunking strategy.
- Built a **CI eval gate in GitHub Actions** that fails pull requests when retrieval
  quality drops, and proved it by injecting a chunking-units bug (MRR 0.87 to 0.50, build
  failed).
- Containerized the vector database with **Docker Compose** (multi-architecture images).
  Verified identical retrieval scores, and diagnosed a Windows IPv6 `localhost` delay that
  cut search latency from **2,062 ms to 7.6 ms (p50)**.
- Engineering: **161 automated tests**, PR-based Git workflow, pinned dependencies and
  model revisions, and every metric traceable to a git commit.
- *In progress:* hybrid search (BM25 + dense, RRF), cross-encoder reranking, **LangGraph**
  agents with human-in-the-loop, guardrails (Presidio, NeMo Guardrails), and deployment with
  **Terraform, Kubernetes (k3s) and AWS**.

---

## Version 2: full project (finished, through deployment)

**DocPilot: Agentic RAG Platform with Hybrid Search, Guardrails and Cloud Deployment**
*Python, LangGraph, RAG, FastAPI, Pydantic, Qdrant (hybrid dense + sparse), Hugging Face
sentence-transformers (BGE embeddings, cross-encoder reranker), Docling, LiteLLM (Groq,
Gemini, OpenRouter, Ollama), MCP, RAGAS, DeepEval, LLM-as-a-judge, NeMo Guardrails,
Microsoft Presidio, Redis, PostgreSQL, MLflow, Docker, Kubernetes (k3s, Amazon EKS),
Terraform, AWS (EC2, S3, ECR, IAM, CloudWatch), Oracle Cloud, Prometheus, Grafana,
GitHub Actions CI/CD*

- Architected an **agentic RAG platform** with **LangGraph** (route, retrieve, grade,
  rewrite, **human-in-the-loop** review) that answers questions over technical docs, AI/ML
  papers and interview notes (Markdown, PDF, Word) with citations and calibrated refusals.
- Engineered the ingestion pipeline (**Docling** PDF/DOCX parsing, cleaning, token-aware
  chunking) and chose the chunking strategy with an **11-configuration ablation**:
  **Recall@1 0.54 to 0.63** on dev, 0.35 to 0.47 on held-out test.
- Built **hybrid retrieval**: dense BGE plus sparse **BM25** vectors in **Qdrant**, fused
  with **Reciprocal Rank Fusion**, **cross-encoder reranking**, query transforms
  (multi-query, HyDE) and metadata filters. Raised Recall@5 from 0.78 to **[X]** and MRR
  from 0.65 to **[X]**, with p50/p95 latency measured per stage.
- Designed a full **evaluation stack**: a 65-question golden set with verbatim evidence,
  hand-written Recall@k/MRR/nDCG, **LLM-as-a-judge** faithfulness (validated against human
  spot-checks, agreement **[X]%**), cross-checked with **RAGAS/DeepEval**, all tracked in
  **MLflow**. A **CI eval gate** in GitHub Actions blocks pull requests that degrade retrieval.
- Implemented **guardrails** against direct and indirect **prompt injection**, PII leakage
  (**Presidio**) and unsafe tool use (**NeMo Guardrails**). Measured on a red-team set:
  attack success rate **[X]% to [X]%**, false-block rate **[X]%**.
- Productionized with **FastAPI** (async, SSE streaming, API-key auth), **Redis** rate
  limiting and semantic caching, **LiteLLM** fallbacks across free LLM providers, and an
  **MCP server**. Deployed multi-architecture **Docker** images to **Kubernetes (k3s)** with
  **Terraform** on **AWS**, then Oracle Cloud. Monitored with **Prometheus/Grafana**; p95
  latency **[X] s**, at a cost of **$0 per month**.

---

## Skills line (ATS keywords)

**True today:** Python · Generative AI · LLMs · RAG · Prompt Engineering · Embeddings ·
Vector Databases (Qdrant) · Hugging Face · sentence-transformers · Docling · FastAPI ·
Pydantic · LLM Evaluation (Recall@k, MRR, nDCG) · MLflow · Docker · Docker Compose ·
GitHub Actions · CI/CD · pytest · Git

**Add as each one is built:** LangGraph · AI Agents · Hybrid Search · BM25 · Reranking ·
RAGAS · DeepEval · LLM-as-a-Judge · Guardrails · Prompt Injection Defense · Presidio ·
LiteLLM · MCP · Redis · PostgreSQL · Kubernetes · Terraform · AWS · Prometheus · Grafana

---

## Two-line version (LinkedIn, project summary)

> Built DocPilot, an evaluation-driven RAG assistant over technical docs, AI/ML papers and
> interview notes (PDF, Word, Markdown): hand-built eval harness and 65-question golden set,
> 11-config chunking ablation (Recall@1 0.54 to 0.63), CI eval gate on GitHub Actions,
> Dockerized Qdrant. Now adding hybrid search, reranking, LangGraph agents and cloud deployment.

## Before you send it: checklist

- [ ] Every number matches `evals/ABLATION.md` or the decision log (and you can say how it
      was measured)
- [ ] Every tool you list is one you can show in the code
- [ ] You can explain each bullet out loud in 30 seconds
- [ ] No `[X]` left anywhere
- [ ] Add the repo link only once it is public (end of project, your choice)

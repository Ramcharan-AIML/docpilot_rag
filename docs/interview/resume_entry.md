# Resume Entry: DocPilot

Copy-ready text for your resume and LinkedIn. **Rule:** list only what is built and
measured at the moment you send the resume. Interviewers ask about every word; a skill you
have not built yet is the fastest way to lose trust. Update this file at every phase gate.

---

## Title (pick one)

1. **DocPilot: Evaluation-Driven RAG Assistant for Technical Documentation** (recommended now)
2. **DocPilot: Agentic RAG Platform with Hybrid Search, Guardrails and Cloud Deployment**
   (use after Phases 3-7 are done)
3. **DocPilot: Production-Grade GenAI Assistant over Docs, PDFs and Word Files** (after 2.7 + 7)

Why title 1 now: "evaluation-driven" is true today, rare among student projects, and is
exactly what AI-engineer interviewers probe. Words like "agentic" or "production-grade"
must wait until those phases exist.

---

## Version A: use NOW (Phase 1 done, Phase 2 started, 2026-10-15)

**DocPilot: Evaluation-Driven RAG Assistant for Technical Documentation**
*Python, FastAPI, Qdrant, Hugging Face (BGE embeddings), LLM API (Groq, OpenAI-compatible), MLflow, pytest, GitHub Actions*

- Built an end-to-end Retrieval-Augmented Generation pipeline (ingestion, chunking,
  384-dim BGE embeddings, Qdrant vector search, cited LLM answers) served through a
  **FastAPI** `/ask` endpoint with Pydantic validation.
- Designed an **evaluation harness from scratch**: a 32-question golden dataset labelled
  by verbatim evidence (dev/test split, 16% unanswerable "near-miss" questions) with an
  automatic validator; metrics **Recall@k, MRR, nDCG, abstention accuracy and per-stage
  p50/p95 latency**, written and unit-tested by hand.
- Established a measured baseline: **Recall@5 0.84, MRR 0.67** (dev), **abstention
  accuracy 0.91 with zero made-up answers** on unanswerable questions, **p50 1.1 s**
  warm latency, and showed the LLM is ~96% of response time.
- Used error analysis to trace failures to **ingestion and ranking** (Recall@1 0.53 vs
  Recall@5 0.84; a correct-looking answer containing invented code), which set the
  roadmap for structure-aware chunking and reranking.
- Engineering practice: **66 automated tests**, **CI on GitHub Actions** (lint, tests,
  file-size rule), PR workflow, pinned dependencies and model revisions, every metric
  traceable to a git commit, experiment tracking in **MLflow**.

## Version B: target when the project is complete (fill numbers only from real runs)

**DocPilot: Agentic RAG Platform with Hybrid Search, Guardrails and Cloud Deployment**
*Python, LangGraph, FastAPI, Qdrant (hybrid dense + sparse), cross-encoder reranking,
Docling (PDF/Word), MLflow, RAGAS/DeepEval, guardrails (NeMo / Presidio), Docker,
Kubernetes (k3s), Terraform, AWS, Prometheus/Grafana, GitHub Actions*

- Agentic RAG with **LangGraph** (route, retrieve, grade, rewrite, human-in-the-loop)
  over technical docs, AI/ML learning material and interview notes, including **PDF and
  Word** documents parsed with Docling.
- Improved retrieval from the C0 baseline (Recall@5 0.84, MRR 0.67) to **[n/a until
  measured]** via structure-aware chunking, **hybrid search (RRF)** and a **reranker**;
  each change measured in an ablation table with its latency cost.
- Generation quality measured with an **LLM-as-a-judge** (faithfulness, relevancy),
  validated against hand labels and compared with RAGAS/DeepEval: **[n/a]**.
- **Guardrails** against prompt injection and PII: attack success rate **[n/a]** ->
  **[n/a]**, false-block rate **[n/a]**.
- Deployed with **Docker, Terraform and k3s** on cloud free tiers, monitored with
  **Prometheus/Grafana**; CI eval gate blocks pull requests that lower retrieval quality.

---

## Skills line (the keywords recruiters and ATS scanners look for)

**Now (true today):** Python · RAG · LLMs · Prompt engineering · Embeddings ·
Vector databases (Qdrant) · Hugging Face / sentence-transformers · FastAPI · Pydantic ·
LLM evaluation (Recall@k, MRR, nDCG, abstention, latency) · MLflow · pytest ·
GitHub Actions (CI) · Git

**Add only when built:** LangGraph / AI agents · Hybrid search · Reranking · RAGAS /
DeepEval · LLM-as-a-judge · Guardrails · Docling (PDF/Word parsing) · Docker ·
Kubernetes · Terraform · AWS · Prometheus / Grafana

Why these matter to recruiters: AI-engineer job posts ask most for **RAG, vector
databases, LLM APIs, evaluation, agents (LangGraph), FastAPI, Docker/Kubernetes and a
cloud**. Evaluation and deployment are what separate an "engineer" from a "tutorial"
project.

---

## Two-line version (LinkedIn headline, project summary)

> Built DocPilot, an evaluation-driven RAG assistant over technical docs: hand-built eval
> harness (Recall@5 0.84, MRR 0.67, 0.91 abstention, p50 1.1 s), FastAPI service, CI and
> MLflow experiment tracking; now adding structure-aware chunking, hybrid search and agents.

## Before you send it: checklist

- [ ] Every number matches `evals/ABLATION.md` (and you can say how it was measured)
- [ ] Every tool listed is in the code you can show
- [ ] You can explain each bullet out loud in 30 seconds (`docs/teaching/2_evals_guide.md`)
- [ ] Repo link added only once it is public (end of project, by your choice)

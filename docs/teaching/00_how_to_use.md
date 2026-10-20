# Teaching Notes: How to Use This Folder

The implementation plan tells you **what** to build. These notes tell you **why it works**,
**why we picked it**, and **what is happening inside**, in simple English.

## The reading routine for each phase

1. Read the teaching file for the phase **before** writing code (30 to 45 minutes).
2. Build each step from the plan, one at a time.
3. After each step, come back to its section here and re-read the "What is happening"
   part. It will make much more sense once you have seen the output.
4. At the end of the phase, answer the self-check questions without looking.
5. Then open `docs/interview/phase_N_interview.md`, cover the answers, and try them.

## The shape of every teaching section

- **Like I'm five:** an everyday analogy.
- **What it really is:** the precise version.
- **What is happening when it runs:** step by step, with file names.
- **Why this / why not that:** our choice against the obvious alternatives.
- **Common mistakes:** what beginners (and AI-generated code) get wrong.

## Files

| File | Covers |
|---|---|
| `phase_0_foundations.md` | Project setup, virtual environments, git hygiene, embeddings, cosine similarity, keyword vs meaning search |
| `phase_1_baseline.md` | RAG end to end, chunking, vector DBs, prompts, evals (Recall, MRR, nDCG), golden datasets, FastAPI primer |
| `phase_2_chunking.md` | Data cleaning, parsing, six chunking strategies, tokens, metadata, ablation thinking |
| `phase_3_retrieval.md` | Docker primer, BM25, hybrid search, RRF, rerankers, query transforms, embedding choice, filters, LLM-as-judge |
| `phase_4_agents.md` | What an agent is, agentic RAG, LangGraph primer, structured output, loop caps, agent vs no agent |
| `phase_5_multiagent_hitl.md` | Tools and function calling, safe tools, supervisor pattern, checkpoints, human-in-the-loop, MCP |
| `phase_6_guardrails.md` | Guardrails primer, threat model, prompt injection (direct and indirect), PII, output checks, red-teaming, measuring safety |
| `phase_7_production.md` (+ `2_`) | Async APIs, streaming, auth, rate limits, caching, gateways, observability, Docker images, Compose, CI/CD, cloud deploy, HTTPS, load tests |
| `phase_8_stretch.md` | GraphRAG, DSPy, ColBERT, ColPali, trajectory evals |
| `big_picture_and_reading_runs.md` | The whole project flow (pipeline, phases, where evals fit) and how to read every ingest/eval/latency output and conclude a run |

## From-zero primers (read before the phase that uses them)

| Primer | Read before | Covers |
|---|---|---|
| `primer_evals.md` | Phase 1 step 1c | evals from zero: answer key, Recall/MRR/nDCG by hand, judges, ablation, CI gate |
| `evals_guide.md` + `2_evals_guide.md` | after Phase 1 step 1d | complete evals study guide with DocPilot's real C0/L0 numbers, plus direct and scenario interview questions with answers |
| `primer_git_workflow.md` | Phase 1 | branches, pull requests, CI, branch protection, tags |
| `primer_mlflow.md` | Phase 2 | experiment tracking; MLflow vs tracing |
| `primer_object_storage.md` | Phase 3 | S3 ideas, SeaweedFS (MinIO replacement), boto3 |
| `primer_guardrails.md` | Phase 6 | guardrails from zero: threats, layers, canary, red team, two numbers |
| `primer_latency.md` | Phase 1 step 1a.8 | latency before and after deployment: p50/p95, per stage, cold vs warm, TTFT, load, how to measure honestly |
| `primer_rag_monitoring.md` | Phase 7 | monitoring AI on live traffic: scores, groundedness, refusals, drift |
| `primer_aws.md` + `2_primer_aws.md` | Phase 7 | cloud basics, free plan, IAM, VPC, EC2, S3, ECR, CloudWatch, cost traps, Oracle move |
| `primer_terraform.md` | Phase 7 | infrastructure as code, state, portable layout |
| `primer_kubernetes.md` | Phase 7 | Kubernetes words, Compose-to-K8s, k3s, EKS exercise |

## One idea that connects everything

> **Build the simplest version, measure it, change one thing, measure again, keep it only
> if the number says so.**

Every phase is this loop. If you remember only one sentence for interviews, remember this.

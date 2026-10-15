# Implementation Plan: Overview

This folder answers one question: **what do we build next, in which file, and how do we
know it worked?** The "why" behind each concept lives in `docs/teaching/`, and the interview
questions live in `docs/interview/`. Read the three together, phase by phase.

| Phase | Plan file | Teaching file | Interview file | Time at ~5 h/day |
|---|---|---|---|---|
| 0 Foundations | `phase_0_foundations.md` | `teaching/phase_0_foundations.md` | `interview/phase_0_interview.md` | 1-2 days |
| 1 Baseline + evals + mini API + Git workflow/CI | `phase_1_baseline.md`, `2_phase_1_baseline.md` | `teaching/phase_1_baseline.md`, `primer_evals.md`, `primer_git_workflow.md` | `interview/phase_1_interview.md` | ~1 week |
| 2 Ingestion + chunking + MLflow + CI eval gate | `phase_2_chunking.md` | `teaching/phase_2_chunking.md`, `primer_mlflow.md` | `interview/phase_2_interview.md` | ~1 week |
| 3 Retrieval upgrade + Docker + SeaweedFS/boto3 | `phase_3_retrieval.md` | `teaching/phase_3_retrieval.md`, `primer_object_storage.md` | `interview/phase_3_interview.md` | ~1-1.5 weeks |
| 4 Agentic RAG | `phase_4_agents.md` | `teaching/phase_4_agents.md` | `interview/phase_4_interview.md` | ~1 week |
| 5 Multi-agent, tools, MCP, HITL | `phase_5_multiagent_hitl.md` | `teaching/phase_5_multiagent_hitl.md` | `interview/phase_5_interview.md` | 1-1.5 weeks |
| 6 Guardrails | `phase_6_guardrails.md` | `primer_guardrails.md`, `teaching/phase_6_guardrails.md` | `interview/phase_6_interview.md` | ~1 week |
| 7 Production: app, CI/CD, AWS, Terraform, k3s, EKS exercise, RAG monitoring, Oracle move | `phase_7_production.md` + `2_`, `3_`, `4_` | `teaching/phase_7_production.md` + `2_`, `primer_aws.md` + `2_`, `primer_terraform.md`, `primer_kubernetes.md`, `primer_rag_monitoring.md` | `interview/phase_7_interview.md` + `2_` | 2.5-3 weeks |
| 8 Stretch | `phase_8_stretch.md` | `teaching/phase_8_stretch.md` | `interview/phase_8_interview.md` | optional |

Total: about **10 to 12 weeks** (the original 8-10, plus about 2 weeks for AWS, Terraform,
Kubernetes, and monitoring). Scope is the biggest risk, so the gates are strict.

---

## Where each technology appears

| Technology | First used | Plan step | Primer (from zero) |
|---|---|---|---|
| Evals (retrieval, judge, agent, red-team) | Phase 1 | 1c-1d, 3.9, 4.5, 5.7, 6.1 | `teaching/primer_evals.md` |
| Git workflow: feature branches, PRs, protection, tags | Phase 1 | 1f, 2.10 | `teaching/primer_git_workflow.md` |
| MLflow experiment tracking | Phase 2 | 2.0, 3.1b | `teaching/primer_mlflow.md` |
| CI eval gate | Phase 2 | 2.10 | `teaching/primer_evals.md` section 8 |
| Docker / Compose | Phase 3 | 3.1, 7.8-7.9 | `teaching/phase_3_retrieval.md` section 1 |
| SeaweedFS + boto3 (S3-compatible; replaces MinIO) | Phase 3 | 3.1b | `teaching/primer_object_storage.md` |
| Guardrails | Phase 6 | 6.1-6.8 | `teaching/primer_guardrails.md` |
| RAG monitoring (Prometheus, Grafana) | Phase 7 | 7.6-7.7 | `teaching/primer_rag_monitoring.md` |
| AWS: IAM, VPC, EC2, S3, ECR, CloudWatch | Phase 7 | 7.10-7.13 | `teaching/primer_aws.md`, `2_primer_aws.md` |
| Terraform | Phase 7 | 7.11-7.12, 7.15, 7.18 | `teaching/primer_terraform.md` |
| Kubernetes (k3s, planned) | Phase 7 | 7.14 | `teaching/primer_kubernetes.md` |
| EKS (exercise only) | Phase 7 | 7.15 | `teaching/primer_kubernetes.md` section 6 |
| Oracle Cloud (long-term home) | Phase 7 / month 5 | 7.18 | `teaching/2_primer_aws.md` section 13 |

---

## How every step in the plan is written

Each step has the same parts:

- **Goal**: one sentence.
- **Files**: exactly which files are created or changed.
- **Code**: a sketch with comments. Library calls marked `# VERIFY:` are checked against
  current docs on build day (Rule 4) before we trust them.
- **Run**: the command to run (PowerShell on Windows).
- **Done when**: a check you can see with your own eyes.

---

## The big flow of the project

```text
Phase 0  understand vectors
   │
Phase 1  build the simplest thing that works  ──▶  measure it (C0)  ──▶  wrap in an API
   │
Phase 2  fix the data, try 6 ways to cut it   ──▶  measure each (C1-C5)
   │
Phase 3  search better (hybrid, rerank, rewrite questions)  ──▶  measure (C6-C8)
   │
Phase 4  let an LLM manage the steps          ──▶  measure: better? slower? (C9)
   │
Phase 5  more agents, tools, a human reviewer ──▶  measure (C10)
   │
Phase 6  defend it                            ──▶  measure attacks and false blocks (C11)
   │
Phase 7  ship it: API, Docker, CI/CD, AWS via Terraform, k3s, RAG monitoring, then move to Oracle
   │
Phase 8  optional research toys
```

The pattern never changes: **build, measure, keep only what the numbers support.**

---

## Commands you will use all the time (Windows PowerShell)

```powershell
# activate the virtual environment (every new terminal)
.venv\Scripts\Activate.ps1

# run tests
pytest -q

# lint and format
ruff check .
ruff format .

# run a retrieval eval (from Phase 1d)
python evals/run_retrieval_eval.py --collection docpilot_naive --split dev

# check the 500-line rule (Git Bash)
git ls-files | xargs wc -l | awk '$1 > 500 && $2 != "total"'
```

---

## The gate checklist (copy into progress.md at each gate)

- [ ] `pytest` green
- [ ] eval run recorded in `evals/ABLATION.md` (real numbers)
- [ ] `docs/decisions.md` updated, versions pinned with "verified on" dates
- [ ] learner wrote `docs/interview_notes.md` answers in own words
- [ ] `docs/progress.md` updated
- [ ] no file over 500 lines
- [ ] `git tag phase-N`

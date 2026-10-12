# Interview Preparation: How to Use This Folder

Each phase file has questions the way a real interviewer asks them about **this project**,
followed by a model answer, the likely follow-up, and the answer that loses the interview.

## How to practise

1. Cover the answer. Say your answer **out loud** (interviews are spoken).
2. Compare with the model answer. Note what you missed.
3. Write your own version in `docs/interview_notes.md`, in your own words.
4. Wherever you see `[your number: n/a]`, replace it with the real number from
   `evals/ABLATION.md` once you have it. **Never invent a number** in an interview either.
   "I measured X on a 60-question dev set" beats any vague claim.

## The answer pattern that works

For "why did you choose X?" questions, use **C-A-E-T**:

- **C**ontext: what problem you had.
- **A**lternatives: what else you considered.
- **E**vidence: the number or test that decided it.
- **T**rade-off: what it cost, and when you would choose differently.

## Files

| File | Phase |
|---|---|
| `challenges_and_failures.md` | Real big failures and fixes, for "where did you get stuck?" |
| `phase_0_interview.md` | Embeddings, setup |
| `phase_1_interview.md` | RAG baseline, evals, FastAPI |
| `phase_2_interview.md` | Data quality, chunking |
| `phase_3_interview.md` | Hybrid search, reranking, query transforms, judges, Docker |
| `phase_4_interview.md` | Agents, LangGraph |
| `phase_5_interview.md` | Tools, multi-agent, HITL, MCP |
| `phase_6_interview.md` | Guardrails, security |
| `phase_7_interview.md` | Production, deployment, CI/CD, observability |
| `2_phase_7_interview.md` | AWS, Terraform, Kubernetes (k3s, EKS), RAG monitoring, MLflow vs tracing, Git workflow, SeaweedFS |
| `phase_8_interview.md` | Stretch topics |
| `ALL_INTERVIEW_QUESTIONS.md` | Created after the Phase 7 gate: every question merged, real numbers filled in (split into `2_`, `3_` parts per the 500-line rule) |

## The two opening questions you will always get

**"Tell me about this project in two minutes."** Practise this at every gate; it grows as
the project grows. Structure: problem (developers need correct, cited answers from docs;
naive RAG fails on code, tables, exact names) -> what you built (hybrid retrieval, agents,
guardrails, evals, deployment, all free) -> the proof (ablation table: C0 to final, safety
numbers, CI gate) -> one surprise or negative result.

**"What was the hardest part?"** Pick a real moment from `docs/progress.md` or the
decision log. Real stories with numbers beat polished generic ones.

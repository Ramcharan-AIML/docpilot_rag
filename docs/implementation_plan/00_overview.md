# Implementation Plan: Overview

This folder answers one question: **what do we build next, in which file, and how do we
know it worked?** The "why" behind each concept lives in `docs/teaching/`, and the interview
questions live in `docs/interview/`. Read the three together, phase by phase.

| Phase | Plan file | Teaching file | Interview file | Time at ~5 h/day |
|---|---|---|---|---|
| 0 Foundations | `phase_0_foundations.md` | `teaching/phase_0_foundations.md` | `interview/phase_0_interview.md` | 1-2 days |
| 1 Baseline + evals + mini API | `phase_1_baseline.md`, `2_phase_1_baseline.md` | `teaching/phase_1_baseline.md` | `interview/phase_1_interview.md` | ~1 week |
| 2 Ingestion + chunking | `phase_2_chunking.md` | `teaching/phase_2_chunking.md` | `interview/phase_2_interview.md` | ~1 week |
| 3 Retrieval upgrade | `phase_3_retrieval.md` | `teaching/phase_3_retrieval.md` | `interview/phase_3_interview.md` | ~1 week |
| 4 Agentic RAG | `phase_4_agents.md` | `teaching/phase_4_agents.md` | `interview/phase_4_interview.md` | ~1 week |
| 5 Multi-agent, tools, MCP, HITL | `phase_5_multiagent_hitl.md` | `teaching/phase_5_multiagent_hitl.md` | `interview/phase_5_interview.md` | 1-1.5 weeks |
| 6 Guardrails | `phase_6_guardrails.md` | `teaching/phase_6_guardrails.md` | `interview/phase_6_interview.md` | ~1 week |
| 7 Production | `phase_7_production.md`, `2_phase_7_production.md` | `teaching/phase_7_production.md`, `2_...` | `interview/phase_7_interview.md` | 1-1.5 weeks |
| 8 Stretch | `phase_8_stretch.md` | `teaching/phase_8_stretch.md` | `interview/phase_8_interview.md` | optional |

Total: about 8 to 10 weeks. Scope is the biggest risk, so the gates are strict.

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
Phase 7  ship it: Docker, CI gate, cloud, dashboards
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

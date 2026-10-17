# DocPilot Docs: Map

Start here. Every session begins with `progress.md`.

| I want to... | Open |
|---|---|
| Know where we are and what is next | [progress.md](progress.md) |
| Read the step-by-step story of what was done | [USER_GUIDE.md](USER_GUIDE.md), then [2_USER_GUIDE.md](2_USER_GUIDE.md) (from step 1a.3), then [3_USER_GUIDE.md](3_USER_GUIDE.md) (gates, Phase 2) |
| Continue in a new chat without losing context | [CHAT_CONTEXT.md](CHAT_CONTEXT.md) |
| See the rules Claude Code loads every session | [../CLAUDE.md](../CLAUDE.md) |
| Know the rules (500 lines, numbers, secrets, gates) | [RULEBOOK.md](RULEBOOK.md) |
| Read the source of truth (scope, phases, targets) | [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) |
| See the whole system design | [architecture/architecture.md](architecture/architecture.md) -> [part 2](architecture/2_architecture.md) -> [part 3: cloud, infra, MLOps](architecture/3_architecture.md) |
| Know exactly what to build next, file by file | [implementation_plan/00_overview.md](implementation_plan/00_overview.md) |
| Understand the concepts behind a phase | [teaching/00_how_to_use.md](teaching/00_how_to_use.md) |
| Study evals for interviews (concepts + real numbers + Q&A) | [teaching/evals_guide.md](teaching/evals_guide.md), [teaching/2_evals_guide.md](teaching/2_evals_guide.md) |
| Learn a technology from zero (evals, guardrails, latency, Git, MLflow, S3/SeaweedFS, AWS, Terraform, Kubernetes, monitoring) | `teaching/primer_*.md` (list in [teaching/00_how_to_use.md](teaching/00_how_to_use.md)) |
| Practise interview questions per phase | [interview/README.md](interview/README.md) |
| Tell "where did you get stuck?" stories (big failures only) | [interview/challenges_and_failures.md](interview/challenges_and_failures.md) |
| Write my own interview answers | [interview_notes.md](interview_notes.md) |
| See why every choice was made | [decisions.md](decisions.md), [2_decisions.md](2_decisions.md) (D-038 on) |

```text
docs/
├── README.md                  this map
├── PROJECT_DOCUMENTATION.md   source of truth (written by the learner)
├── RULEBOOK.md                rules for every session
├── progress.md                status, next step, session log
├── USER_GUIDE.md              the story so far, step by step, with real results
├── CHAT_CONTEXT.md            handoff summary for a new chat
├── decisions.md               decision log + version pins + free-tier checks
├── 2_decisions.md             decision log continued (D-038 on)
├── interview_notes.md         learner's own answers (own words only)
├── architecture/              target system design (3 parts; part 3 = cloud, infra, MLOps)
├── implementation_plan/       phase-by-phase build steps with file names and code sketches
├── teaching/                  phase-by-phase concepts + from-zero primers (primer_*.md)
└── interview/                 phase-by-phase interview Q&A (+ big merged file after Phase 7)
```

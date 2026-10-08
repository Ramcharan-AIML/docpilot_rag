# Chat Context Handoff (as of 2026-10-08)

Paste this file (or point a new chat at it) to continue without losing context.
This is a **detailed summary** of the conversation, not a word-for-word transcript.
Also read: `CLAUDE.md`, `docs/progress.md`, `docs/USER_GUIDE.md`.

**Suggested first message in a new chat:**
> Read `CLAUDE.md`, `docs/CHAT_CONTEXT.md`, and `docs/progress.md`, then continue as my
> mentor from where we stopped. Do not repeat finished steps.

---

## 1. The original request (master prompt, summarised)

- **Role for the AI:** senior AI Engineer mentor (20 years), teacher first, builder second.
  Goal: a learner who can explain every line, decision, and number in an interview.
- **Learner:** wants an AI Engineer / GenAI Engineer role; needs one outstanding project.
  Python intermediate, FastAPI beginner, Docker beginner, zero guardrails/evals knowledge,
  new to LangGraph, vector DBs, deployment. 32 GB RAM, 2 GB GPU (CPU-only), ~5 h/day.
  Wants simple English, ELI5 analogies, one step at a time, human-readable code that does
  not look AI-generated, a "why not X?" for every choice, honest feedback.
- **Project:** DocPilot, an agentic, hybrid-search RAG assistant over technical docs
  (FastAPI, Docker, LangGraph, Qdrant, Pydantic, Redis): citations, abstains when docs lack
  the answer, asks a human when unsure, defends against prompt injection, proves quality
  with measured evals, deployed publicly. Source of truth: `docs/PROJECT_DOCUMENTATION.md`
  (if it conflicts with the prompt, stop and ask).
- **Hard constraints:** everything free (Groq, Gemini, OpenRouter free, Ollama; local HF
  embeddings/reranker; self-hosted Qdrant, Postgres, Redis, Prometheus, Grafana; Oracle
  Cloud Always Free). Providers swappable. Verify free-tier limits, model names, and library
  APIs against current docs; pin versions; record the date in `docs/decisions.md`. No
  secrets, downloaded docs, models, or vector data in git. Never invent numbers (`n/a` if
  unknown).
- **Must not:** paid services; skip ahead to agents/guardrails/deployment before evals and
  gates; hide logic in frameworks before the raw version; claim results without a run; add
  dependencies without a decision entry; overwhelm the learner.
- **Learner's extra requests:** complete architecture; implementation plan for all phases
  with expanded sub-phases and file names, with commented code; a rule book with a
  **500-line max per file** (continue in `2_...`); a **teaching** folder per phase; an
  **interview** folder per phase with real-interviewer questions and answers, plus one big
  merged file after the project ends; a **progress** file; learn everything (especially
  evals, guardrails, production deployment).

---

## 2. What has been produced

**Session 1 (2026-10-03):** the whole `docs/` system (41 files, all under 500 lines):
`README.md` (map), `RULEBOOK.md` (16 rules), `progress.md`, `decisions.md` (D-001 to D-014),
`interview_notes.md` (learner's own words), `architecture/architecture.md` + `2_...`,
`implementation_plan/00_overview.md` + phase files 0 to 8 (phase 1 and 7 in two parts),
`teaching/00_how_to_use.md` + phase files 0 to 8 (phase 7 in two parts),
`interview/README.md` + `phase_0..8_interview.md`.
`PROJECT_DOCUMENTATION.md` (919 lines) is exempt from the 500-line rule (learner's file).

**Session 5 (2026-10-08):** `docs/USER_GUIDE.md` (step-by-step story), `CLAUDE.md`
(root, auto-loaded rules), this file.

---

## 3. Git history and branches

```text
5a1147d Initial commit
b08c713 docs: add rule book, architecture, phase plans, teaching notes, interview Q&A  (docs/project-plan)
b1fdee0 Merge branch 'docs/project-plan'  (into main, --no-ff)
497a9a4 phase0: project skeleton, pinned dependencies, editable install   (phase-0-foundations)
5924b95 phase0: lab 1 embeddings and cosine similarity                    (phase-0-foundations)
```
Current branch: `phase-0-foundations`. Uncommitted: `labs/lab2_keyword_vs_meaning.py`,
`docs/progress.md`, `docs/interview_notes.md` (learner added Phase 0 questions 3 and 4),
`docs/USER_GUIDE.md`, `docs/CHAT_CONTEXT.md`, `CLAUDE.md`.
Branch plan: `phase-1-baseline`, `phase-2-chunking`, `phase-3-hybrid-retrieval`,
`phase-4-langgraph-agents`, `phase-5-tools-hitl-mcp`, `phase-6-guardrails`,
`phase-7-production`; sub-branches `feat/`, `fix/`, `exp/`, `docs/`.

---

## 4. Steps completed, with real results

**0.1 Skeleton:** `.gitignore` (secrets, `data/docs/*` + `!data/docs/.gitkeep`,
`data/processed/`, qdrant, `*.db`/`*.sqlite`/`*.duckdb`, models, caches, `.venv/`,
`.env.*` + `!.env.example`), `.env.example` (LLM_PROVIDER, LLM_MODEL, GROQ/OPENROUTER/
GEMINI keys, OLLAMA_BASE_URL), `src/docpilot/__init__.py`, `.gitkeep` files. Verified with
`git check-ignore -v`.

**0.2 Environment:** reused clean `.venv`, Python 3.13.2. PyPI checked 2026-10-03:
sentence-transformers 6.1.0, numpy 2.5.3 (needs Python >=3.12), pytest 9.1.1, ruff 0.16.10;
indirect torch 2.14.1+cpu, transformers 5.18.0. Files: `pyproject.toml`
(`requires-python >=3.12`, src layout, ruff E/F/I/B/UP, line length 100),
`requirements.txt`, `requirements-dev.txt`, `requirements-lock.txt` (46 packages).
Decisions D-015 (Python 3.12+), D-016 (requirements split + lock). Plan docs changed to
Python 3.13 for Dockerfile and CI; Dockerfile inline-comment bug fixed.
Learner asked why a lock file is needed; explained (ranges like `torch>=2.2` resolve to the
newest version on install day).

**0.3 Lab 1** (`labs/lab1_embeddings.py`): model card verified 2026-10-07 (384 dims,
512-token limit, MIT, query prefix, Normalize module, revision `5c38ec7c...`, D-002 updated).
Results: validate-question vs Pydantic 0.708; vs cat 0.379; Pydantic vs cat 0.388;
vector length 1.0. Predictions all correct but the learner gave no "why" for the lowest.
Break-it (paraphrase "Make sure the data a client sends is correct."): 0.799 / 0.379 /
0.410; no prediction written; the paraphrase still shared "data" (mentor's own mistake,
admitted). File restored to the original sentences.

**0.4 Lab 2** (`labs/lab2_keyword_vs_meaning.py`, regex word split, picks line, no-prefix
column). Predictions all four correct. Results:
Q1 "what does max_length do": keyword 1/0/0; meaning 0.742/0.539/0.490;
no prefix 0.775/0.592/0.534; both pick doc 1.
Q2 "how do I check incoming data is correct": keyword 0/0/0 (NOTHING);
meaning 0.578/0.659/0.502; no prefix 0.564/0.670/0.529; meaning picks doc 2.
Prefix lowered 5 of 6 scores, changed no winner; widened Q1 gap, narrowed Q2 gap: two
questions are not enough to judge it. The lab did not show meaning search failing.

---

## 5. Open items and pending answers

1. **Learner homework:** two own-words sentences for Lab 2; Phase 0 interview notes
   (including the learner's new questions: "Why do retrieval models handle queries and
   documents differently?" and "What happens to a retriever if you feed it the same document
   twice?"); Lab 1 homework on 0.799 vs 0.708.
2. **Unanswered questions to the learner:** (a) is the old Phase 1a code anywhere?
   (we are rebuilding, so effectively no); (b) Phase 2 gate "C1 to C6" vs table (plan uses
   C1-C5); (c) confirm D-014 (generation evals at step 3.9).
3. **Phase 0 gate** remaining: Lab 2 sentences, interview notes, merge to `main`,
   `git tag phase-0`.
4. **Before Phase 1:** learner needs a free Groq key (or other free provider); verify the
   current free models and limits on build day.

---

## 6. Mentor behaviours that worked (keep them)

- Never run lab result code before the learner predicts; only smoke-test helpers.
- Record predictions in `progress.md` before the run; record real numbers after.
- Point out the learner's gaps (missing "why", missing prediction) and the mentor's own
  mistakes openly.
- Fix plan bugs openly when implementing (punctuation in keyword split, Docker comments).
- Keep each reply to one step; end with the exact commit command and the next step.
- Interpret ties honestly; never over-claim from tiny samples.

---

## 7. Next step

Finish the Phase 0 gate, then start **Phase 1, step 1a.1** (`src/docpilot/config.py`) on
branch `phase-1-baseline`, following `docs/implementation_plan/phase_1_baseline.md`.
Before adding `qdrant-client`, `openai`, `python-dotenv`: check PyPI versions, add
decision entries, pin them.

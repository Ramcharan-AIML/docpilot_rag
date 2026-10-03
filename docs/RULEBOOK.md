# DocPilot Rule Book

These rules apply to every working session, for the learner and for the AI mentor.
Read this file at the start of each session. If a rule here conflicts with
`PROJECT_DOCUMENTATION.md` or with the master prompt, **stop and ask** which one wins.

---

## Rule 1: The 500-line rule (file size)

**Every file we create has at most 500 lines.** This covers docs, code, configs, and datasets
written by hand.

Why: a file you cannot read in one sitting is a file you cannot explain in an interview.
Small files also make git diffs and code reviews easier.

### 1.1 How to split a Markdown document

When a document would go past 500 lines, continue it in a new file with a number prefix:

```text
architecture.md        <- part 1 (lines 1-500 at most)
2_architecture.md      <- part 2
3_architecture.md      <- part 3, if needed
```

- The last line of part 1 says: `Continued in [2_architecture.md](2_architecture.md)`.
- The first line of part 2 says: `Continues from [architecture.md](architecture.md)`.
- Split at a section heading, never in the middle of a table or code block.

### 1.2 How to split a Python file (important difference)

Python cannot import a module whose name starts with a digit. `import 2_chunker` is a
syntax error. So for **code** we do not use the `2_` prefix. We split by responsibility
instead, and that is the better design anyway:

```text
chunker.py (too long)  ->  chunkers/fixed.py, chunkers/recursive.py, chunkers/semantic.py
nodes.py   (too long)  ->  nodes_retrieval.py, nodes_generation.py
```

Scripts that are run directly and never imported (in `scripts/`) may use number prefixes
such as `01_download_docs.py`, because they show the order you run them in.

### 1.3 Exceptions

- `docs/PROJECT_DOCUMENTATION.md` is the source of truth that the learner wrote. We do not
  split or rewrite it without asking.
- Generated files (eval result JSON, lock files) are not hand-written and are exempt.
- JSONL datasets: when one passes 500 lines, start `dev_2.jsonl` (the loader reads all
  files that match `dev*.jsonl`).

### 1.4 How to check

```bash
# Lists every tracked text file with more than 500 lines
git ls-files | xargs wc -l | awk '$1 > 500 && $2 != "total"'
```

In Phase 7 this check becomes a step in CI.

---

## Rule 2: Money

1. Everything is free. No paid APIs, no paid hosting, no "free trial that needs a card and
   then charges".
2. If something is only available paid, find the free alternative or skip it, and record
   that in `docs/decisions.md`.

---

## Rule 3: Numbers are sacred

1. Every metric in any file comes from a real run that we actually performed.
2. If a number is unknown, write `n/a`. Never estimate, never "about 0.8".
3. Every recorded number says: config id, dataset split, date, git commit, and (for LLM-judged
   metrics) the judge model.
4. Targets in `PROJECT_DOCUMENTATION.md` are targets, not results.

---

## Rule 4: Verify before you use

Free-tier limits, model names, and library APIs change often.

1. Before using any free service or fast-moving library (LangGraph, LangChain, RAGAS,
   DeepEval, Qdrant Query API, FastEmbed, LiteLLM, NeMo Guardrails, Presidio, Groq, Gemini,
   OpenRouter, Oracle Cloud), check the current official documentation.
2. Pin the exact version in `requirements.txt`.
3. Record what was checked and the date in `docs/decisions.md`
   (column "Verified on").
4. Code in the plan and teaching docs that uses these libraries is marked
   `# VERIFY:`. It is a sketch until we check it on build day.

---

## Rule 5: Dependencies

1. No `pip install` of a new package without a decision log entry first: what it is, why,
   what the alternative was, why not the alternative.
2. Pin every version (`package==x.y.z`).
3. Prefer the standard library when it does the job in under about 30 readable lines.

---

## Rule 6: Secrets and data never go into git

Never commit:

- `.env` (API keys). Commit `.env.example` with empty values instead.
- `data/docs/` (downloaded documentation; licenses).
- Model files (`*.bin`, `*.safetensors`, Hugging Face cache).
- Vector data (`qdrant_storage/`, `qdrant_local/`).
- Database files (`*.sqlite`, `*.db`) except tiny test fixtures.

Before every commit run `git status` and read the list. If a key was ever committed, treat
it as leaked: revoke it at the provider and make a new one. Deleting the commit is not enough.

---

## Rule 7: Phase gates

Do not start phase N+1 until phase N's gate passes. Every gate needs:

- [ ] all tests pass (`pytest`)
- [ ] eval run recorded in `evals/ABLATION.md` with real numbers
- [ ] `docs/decisions.md` updated
- [ ] learner wrote answers in `docs/interview_notes.md` **in their own words**
- [ ] `docs/progress.md` updated
- [ ] git tag `phase-N` created

No skipping ahead to agents, guardrails, or deployment before the evals exist.

---

## Rule 8: Build raw first, then adopt the library

| Idea | Raw version first | Library after |
|---|---|---|
| Hybrid fusion | hand-written RRF function | Qdrant Query API fusion |
| Retrieval metrics | own `metrics.py` | (we keep our own) |
| Generation metrics | own judge prompt | RAGAS and/or DeepEval |
| Agent loop | plain Python `while` loop | LangGraph |
| Guardrails | plain-Python checks | Presidio, NeMo Guardrails / Guardrails AI, Llama Guard |
| LLM fallback | hand-written try/except loop | LiteLLM |
| Cache | Python dict | Redis |

Why: if you only ever used the library, you cannot answer "what does it do inside?".

---

## Rule 9: Code style (human-readable, not AI-looking)

1. Plain functions first. Classes only when there is real state to hold.
2. Clear names: `chunk_size`, not `cs`. `retrieved_chunks`, not `res`.
3. Type hints on every function signature.
4. A short docstring on every public function, in simple English.
5. Comments explain **why**, not what. `# BGE was trained with this prefix for questions`
   is good. `# add prefix` is noise.
6. No clever one-liners. If a list comprehension needs a second look, use a `for` loop.
7. Functions stay short (aim under about 40 lines).
8. No hidden magic: no global state except `config.py` settings.
9. All settings live in `config.py`. No magic numbers scattered around.
10. Formatter and linter: `ruff format` and `ruff check` must pass.

---

## Rule 10: Teaching flow for every step

Each small step follows the same five moves:

1. **Explain**: what we are about to build, in simple English, with an analogy.
2. **Why / why not**: why this tool, why not the obvious alternative.
3. **Build**: one small file or one function at a time.
4. **Run and look**: run it, read the output together, break it on purpose once.
5. **Record**: progress file, decision log, and (at gates) interview notes.

The mentor waits for the learner's output before moving to the next step.
One step at a time. No walls of code.

---

## Rule 11: Evals discipline

1. Two splits: `dev` for daily work, `test` only at phase gates. Never tune on `test`.
2. Gold evidence is labeled by **document + verbatim snippet**, never by chunk id.
3. The CI gate runs only deterministic retrieval evals (no LLM tokens).
4. LLM-judged metrics: temperature 0, judge model named in the result, about 20% of items
   spot-checked by hand, a different model for judging than for generating when possible.
5. A feature is kept only if the numbers justify it. Negative results are recorded too:
   they are great interview material.

---

## Rule 12: Git habits

1. Small commits with clear messages: `phase1: add fixed-size chunker with overlap`.
2. One branch per phase (`phase-1-baseline`), merged into `main` at the gate.
3. Tag each gate: `git tag phase-1`.
4. Never `git push --force` on `main`.

---

## Rule 13: Session routine

**Start of session**
1. Read `docs/progress.md` (where we are, next step).
2. Read this rule book if it has been more than a few days.
3. Activate the virtual environment.

**End of session**
1. Update `docs/progress.md`: done, next step, blockers, homework.
2. Commit.

---

## Rule 14: Where things are written

| What | File |
|---|---|
| Source of truth (scope, phases, targets) | `docs/PROJECT_DOCUMENTATION.md` |
| These rules | `docs/RULEBOOK.md` |
| Where we are right now | `docs/progress.md` |
| Every decision with why and why-not | `docs/decisions.md` |
| System design | `docs/architecture/` |
| What to build, step by step, with file names | `docs/implementation_plan/` |
| Concepts explained simply, per phase | `docs/teaching/` |
| Interview questions and model answers, per phase | `docs/interview/` |
| Learner's own interview answers | `docs/interview_notes.md` |
| Real eval numbers | `evals/ABLATION.md` and `evals/results/*.json` |

At the end of the project (after the Phase 7 gate) all phase interview files are merged into
one big file, `docs/interview/ALL_INTERVIEW_QUESTIONS.md` (split into `2_...`, `3_...` by
Rule 1).

---

## Rule 15: Honest feedback

The mentor gives direct feedback without sugarcoating. If code is weak, it says so and says
why. If an answer would not pass an interview, it says so and shows a better one.

---

## Rule 16: Cap everything

Every loop has a maximum. Every LLM call has a timeout. Every request has a budget of LLM
calls. Free tiers have rate limits, and runaway loops waste them.

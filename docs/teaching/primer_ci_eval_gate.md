# Primer: GitHub Actions and the CI Eval Gate (step 2.10)

Written 2026-10-20 for a learner who has never used GitHub Actions. Read it once top to
bottom, then once more after you've watched the gate turn red in the demo.

Parts:

1. GitHub Actions in one picture
2. The words you need (workflow, event, job, runner, step, action)
3. Our `ci.yml`, line by line
4. What happens "in the background" when you push
5. The eval gate: the exam, the judge, the baseline
6. Testing the test: what the gate catches and what it doesn't
7. Reading a red check: how to debug
8. Changing the baseline on purpose
9. Limits (private repo, minutes, small exam)
10. Your demo, step by step
11. Self-check

---

## 1. GitHub Actions in one picture

**Like I'm five.** You hand your homework to the teacher. Before the teacher even looks at
it, a robot assistant checks the spelling, does the sums again and runs a small quiz. If
anything fails, the homework comes back with a red cross. GitHub Actions is that robot.

**What it really is.** GitHub rents you a fresh computer in the cloud (Linux, about 4 CPUs)
for a few minutes. It downloads your code onto it, runs the commands you wrote in a YAML
file, and reports the result on your pull request: **green tick** (every command exited
with code 0) or **red cross** (some command exited with a non-zero code).

```
you: git push / open a PR
        │
        ▼
GitHub reads .github/workflows/ci.yml
        │
        ├──▶ fresh Linux machine #1 ── job "test":      ruff, pytest, 500-line rule
        │
        └──▶ fresh Linux machine #2 ── job "eval-gate": build tiny index, sit exam, compare
                                                       (both run at the same time)
        │
        ▼
PR page shows:  ✅ ci / test    ❌ ci / eval-gate   ← one line per job
```

**The key idea is the exit code.** Every program ends with a number: 0 means "fine", and
anything else means "something failed". GitHub only looks at that number. That's why
`check_gate.py` ends with `sys.exit(...)` when the scores drop: the non-zero exit code is
what turns the check red.

---

## 2. The words you need

| Word | Meaning | In our file |
|---|---|---|
| **workflow** | one YAML file in `.github/workflows/` | `ci.yml` (name: `ci`) |
| **event** (`on:`) | what starts the workflow | any pull request, and pushes to `main` |
| **job** | a group of steps on **one fresh machine** | `test` and `eval-gate` |
| **runner** | the machine that runs a job | `runs-on: ubuntu-latest` |
| **step** | one command or one ready-made action | `- name: Tests` / `run: pytest -q` |
| **action** (`uses:`) | a reusable step someone published | `actions/checkout@v7.0.1` downloads your code |
| **check** | the result of one job, shown on the PR | `ci / eval-gate` ✅ or ❌ |
| **log** | everything the job printed | click the check, then "Details" |

**Jobs don't share anything.** Each one starts on an empty machine. That's why
`eval-gate` installs Python, torch and the project again, even though `test` just did.
It costs a few minutes, but the two run side by side, so you wait about as long as one job.

---

## 3. Our `ci.yml`, line by line (the `eval-gate` job)

```yaml
eval-gate:                          # the job's name; the PR check is called "ci / eval-gate"
  runs-on: ubuntu-latest            # rent a fresh Linux machine
  timeout-minutes: 20               # a stuck job is killed instead of burning free minutes
  steps:
    - uses: actions/checkout@v7.0.1          # 1. copy the repo (this commit) onto the machine
    - uses: actions/setup-python@v7.0.0      # 2. install Python 3.13
      with: {python-version: "3.13", cache: pip}   # cache: re-use downloads next time
    - name: Install CPU-only torch           # 3. torch without GPU parts (saves GBs)
      run: pip install torch==2.14.1 ...
    - name: Install project                  # 4. our requirements + our package
      run: pip install -r requirements-dev.txt && pip install -e .
    - name: Retrieval eval gate              # 5. THE GATE: exit 0 = ✅, exit 1 = ❌
      run: python scripts/ci_gate.py
```

**Why pin versions (`@v7.0.1`, `torch==2.14.1`)?** So the robot runs the same thing every
time. "Latest" can change overnight and break a check that has nothing to do with your
change.

**Why no secrets?** The gate makes no LLM calls (D-011: retrieval-only, deterministic,
free). No API key is stored on GitHub, so nothing can leak.

---

## 4. What happens "in the background" when you push

When you open a PR, this is what happens on GitHub's side, with times measured on your
laptop for the parts we can run locally:

1. GitHub starts **two** cloud machines, one per job.
2. Each one downloads the repo and installs everything (a few minutes; the `pip` cache
   speeds up later runs).
3. **`test`** runs ruff, then the 160 tests, then the 500-line rule.
4. **`eval-gate`** runs `python scripts/ci_gate.py`, which does three things:

   | Step | What it does | Laptop time |
   |---|---|---|
   | 1/3 ingest | reads the 7 Lumen pages in `tests/fixtures/corpus/`, cleans them, cuts them with **the app's own recipe** (`config.INGEST_ARGS` = FT-200), embeds the 14 chunks and stores them in a **temporary** Qdrant folder | ~4 s (+ loading the model) |
   | 2/3 exam | asks the 18 answerable questions in `evals/golden/ci.jsonl` and scores Recall@5 and MRR, exactly like the dev eval | ~1 s of search |
   | 3/3 judge | `evals/check_gate.py` compares the scores with `evals/baseline_ci.json` | instant |

   On the laptop the whole command took about 48 s, mostly loading the model.
5. Both checks appear on the PR page. Red means don't merge.

**Nothing touches your real index.** The gate sets three environment variables
(`DOCPILOT_DOCS_DIR`, `DOCPILOT_QDRANT_PATH`, `DOCPILOT_MANIFEST_DIR`) only for its own
child processes. `config.py` reads them, and everything goes to a temporary folder that's
deleted at the end. You can run `python scripts/ci_gate.py` on the laptop at any time.

---

## 5. The eval gate: the exam, the judge, the baseline

**Like I'm five.** Your best score on a small practice quiz is written on the wall (the
**baseline**). After every change you take the quiz again. If you score clearly worse than
the wall, the alarm rings. A tiny dip is forgiven, because nobody scores exactly the same
every time (the **tolerance**).

| Part | File | Content |
|---|---|---|
| Library | `tests/fixtures/corpus/ci_fixture/*.md` | 7 short pages about **Lumen**, a made-up task-queue library. We wrote them ourselves, so there's no licence issue and nothing to download. They include prose, code blocks, a settings table, an error-code table and exact names. Several pages talk about retries, timeouts and workers on purpose: these **distractors** make ranking matter. |
| Exam | `evals/golden/ci.jsonl` | 18 answerable questions plus 1 not-in-docs, with the same fields and the same validator as the real golden set |
| Score on the wall | `evals/baseline_ci.json` | Recall@5 **1.000**, MRR **0.870** (commit `cfd01a5`, FT-200, 18 questions) |
| Allowed wobble | same file | Recall@5 0.06, MRR 0.05, and **the reason is written next to them** |
| Judge | `evals/check_gate.py` | fails if `now < baseline - tolerance` for either metric |

**Why these tolerances?** With 18 questions:
- One question is 1/18 = **0.056** of Recall@5. A tolerance of 0.06 forgives one miss.
- One answer slipping from rank 1 to rank 2 costs 0.5/18 = **0.028** of MRR. A tolerance of
  0.05 forgives about one such slip.

The reason we forgive anything at all: the CI machine is Linux, your laptop is Windows, and
tiny floating-point differences can flip two chunks with nearly equal scores. A real break
is far bigger (see part 6).

**Why only Recall@5 and MRR?** It's what the plan specified (D-011, plan 2.10), and they're
the two headline numbers in `ABLATION.md`. MRR is the sensitive one here: with only 14
chunks, "top 5" already covers a third of the library, so Recall@5 only drops on big breaks.

---

## 6. Testing the test: what the gate catches and what it doesn't

**An alarm you never tested is a decoration.** Before trusting the gate, we broke the
pipeline on purpose and watched the numbers (2026-10-20, laptop):

| Break (one change) | Chunks | Recall@5 | MRR | Gate |
|---|---|---|---|---|
| none: the app's FT-200 recipe | 14 | 1.000 | 0.870 | ✅ pass |
| **units bug:** `fixed` (characters) instead of `fixed_tokens` | 42 | 0.778 | 0.495 | ❌ fail |
| chunk size 50 tokens instead of 200 | 44 | 0.833 | 0.494 | ❌ fail |
| chunk size 30 tokens | 68 | 0.667 | 0.480 | ❌ fail |
| **query prefix removed** (`BGE_QUERY_PREFIX = ""`) | 14 | 1.000 | 0.870 | ✅ **not caught** |

**The surprise in the last row.** The plan suggested "remove the BGE query prefix" as the
demo break, but on this small exam it changes nothing. So we checked the **real** dev set
without the prefix: Recall@5 0.805 (same as with it), R@1 0.585 vs 0.634 (2 questions
fewer at rank 1), MRR 0.681 vs 0.701. **The prefix helps a little, and only with ranking.**
That effect is smaller than the gate's tolerance, so the gate can't see it.

**Honest conclusion.** The gate catches **big** breaks: chunking units, sizes, a broken
cleaner or embedder, a search bug. It doesn't catch **small** ranking changes. Small changes
are what the full dev eval (`run_retrieval_eval --split dev`) is for, and you run that by
hand for every change that touches retrieval. A bigger CI exam would be more sensitive but
slower. Revisit this in Phase 3 (D-048).

**Interview line:** *"I tested my eval gate by breaking the pipeline on purpose. It caught
a units bug (MRR 0.87 to 0.50), but not removing the query prefix. I measured that on the
real dev set: about 2 questions at rank 1, below the gate's tolerance. So the gate is
for big regressions, and the full eval is for small ones."*

---

## 7. Reading a red check: how to debug

1. On the PR page, click **Details** next to the red ❌ `ci / eval-gate`.
2. Open the failed step ("Retrieval eval gate"). Scroll to the end. You'll see:
   ```
   metric      baseline       now     floor  result
   recall@5         1.0     0.778      0.94  FAIL
   mrr             0.87     0.495      0.82  FAIL
   Gate FAILED: retrieval got worse than the baseline
   ```
3. **Reproduce it on the laptop:** `python scripts/ci_gate.py` gives the same table. Above
   it, the full per-type table and the `chunks:` line show where things went wrong (42 chunks
   instead of 14 means the chunking changed).
4. Fix the code and push again. The PR re-runs the checks by itself.

If the job fails **before** the gate (the install steps), it's not a quality problem. It's a
dependency or network problem: read the first red line of the log.

---

## 8. Changing the baseline on purpose

The wall score changes only when **you decide** the new numbers are right:
- a real improvement was kept (for example, after the Phase 3 reranker), or
- the fixture pages or `ci.jsonl` were changed on purpose.

```powershell
python scripts/ci_gate.py --update-baseline "Phase 3 reranker kept: MRR 0.87 -> 0.94 (D-0xx)"
```

`--update-baseline` won't run without a reason. Commit `evals/baseline_ci.json` in the same
PR, and write the reason in the PR description. **Never lower the baseline just to make a
red check green.** That's switching the alarm off, not fixing the fire.

Don't run `ruff format` on the fixture pages. They're excluded in `pyproject.toml`,
because ruff once rewrote the Python example inside `tasks.md`, and that would change the
chunks and the scores.

---

## 9. Limits (honest)

- **Private repo, so no required checks.** GitHub only lets a check *block* a merge
  (branch protection) on public repos, or with a paid plan for private ones (D-035). The
  red cross still shows, but the merge button still works. **Our rule: never merge on red.**
  Once the repo goes public at the end, we'll make `ci / test` and `ci / eval-gate`
  required.
- **Free minutes.** Private repos get a monthly budget of free Actions minutes (check
  *Settings → Billing* on GitHub for your current number). Each PR uses two jobs of a few
  minutes each, because of the torch install. `timeout-minutes: 20` caps a stuck job.
- **Small exam.** It catches big breaks, not small ranking changes (part 6).
- **The gate tests the app's recipe.** `config.INGEST_ARGS` is shared by the app and the
  gate. If Phase 3 changes the recipe, the gate follows automatically, and the baseline is
  updated on purpose (part 8).

---

## 10. Your demo, step by step ("prove it", plan 2.10 step 5)

The goal is to open a PR with a deliberate break, watch `eval-gate` turn red, take a
screenshot, and throw the PR away. You need about 10 minutes, most of it waiting.

**Before you start:** step 2.10 must be committed and pushed. Do the normal commit first.

1. Make a throw-away branch:
   ```powershell
   git switch -c demo/broken-gate
   ```
2. In VS Code, open `src/docpilot/config.py`, find the line that starts with
   `INGEST_ARGS = [` and change **one word**: `"fixed_tokens"` → `"fixed"`. Save.
   (That's the units bug: 200 now means characters, not tokens.)
3. Check it locally first. Prediction: pass or fail?
   ```powershell
   python scripts/ci_gate.py
   ```
4. Commit, push, and open the PR into the phase branch:
   ```powershell
   git commit -am "DEMO: chunking units bug on purpose (eval gate must fail)"
   git push -u origin demo/broken-gate
   gh pr create --base phase-2-chunking --title "DEMO: units bug, eval gate must fail" --body "Deliberate break to prove the CI eval gate works (plan 2.10 step 5). Will be closed, never merged."
   ```
5. Watch the checks live (Ctrl+C stops watching, not the checks):
   ```powershell
   gh pr checks --watch
   ```
   Expected: `test` ✅ and `eval-gate` ❌. Open the PR in the browser with `gh pr view --web`,
   click **Details** on eval-gate, and **take a screenshot** of the FAIL table. Save it as
   `docs/interview/assets/phase2_eval_gate_red.png`.
6. Throw the demo away and go back:
   ```powershell
   gh pr close --delete-branch
   git switch phase-2-chunking
   git branch -D demo/broken-gate
   ```

---

## 11. Self-check

1. What turns a GitHub check red? (Hint: one number.)
2. Why does `eval-gate` install torch again when `test` already did?
3. What three things does `scripts/ci_gate.py` do, and why does it never touch your real index?
4. Why is MRR the sensitive metric on this exam and Recall@5 not?
5. The gate didn't catch removing the query prefix. Is the gate broken? What catches it instead?
6. When is it right to update `baseline_ci.json`, and what must the PR say?
7. Why can't we make the check "required" yet?

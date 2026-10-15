# Primer: The Git Workflow (branches, pull requests, protection, tags)

Used from: Phase 1 onward. Plan steps: `implementation_plan/2_phase_1_baseline.md` step 1f,
`implementation_plan/phase_2_chunking.md` step 2.10. Decision: D-024.

---

## 1. Like I'm five

Imagine the project is a **printed book** that people read (`main`).

- You never scribble directly in the printed book. You write a **draft copy** first
  (a **branch**).
- When the draft is ready, you hand it to an **editor** and ask "may I put this into the
  book?" That request is a **pull request (PR)**.
- Before the editor even looks, a **robot checker** reads the draft: spelling, page count,
  and "is the story still as good as before?" That robot is **CI** (continuous integration).
- A **house rule** says: nothing goes into the printed book unless the robot says OK and the
  draft went through a PR. That rule is **branch protection**.
- When a whole chapter is finished, you put a **sticker** on that version of the book:
  "Edition: Phase 1". That sticker is a **tag**.

---

## 2. The words, precisely

| Word | What it really is |
|---|---|
| Commit | A saved snapshot of your files, with a message. Has a unique id (e.g. `5924b95`) |
| Branch | A movable name pointing at a line of commits. Making one is instant and free |
| `main` | The branch that always works. The public, "printed" version |
| Merge | Combining one branch's commits into another |
| Pull request | A GitHub page that proposes merging branch A into branch B, shows the diff, runs CI, and records the review |
| CI | Automatic checks (GitHub Actions) that run on every push / PR |
| Status check | One CI job's result (green tick or red cross) shown on the PR |
| Branch protection | GitHub settings on a branch: require PR, require green checks, block force-push and deletion |
| Tag | A permanent label on one commit, e.g. `phase-1`. Unlike a branch, it never moves |
| Remote / `origin` | The copy of the repo on GitHub |

---

## 3. Our branching model

```text
main  ●────────────────●──────────────────────●────────▶   (protected; tags phase-0, phase-1 ...)
       \              / \                      /
        phase-1-baseline ●──●──●──●──●─────────●            (one branch per phase)
              \         /      \           /
               feat/chunker     feat/eval-metrics           (one small branch per step)
```

| Branch type | Example | Lives for | Merged into | How |
|---|---|---|---|---|
| Phase | `phase-1-baseline` | one phase (~1 week) | `main` at the gate | PR, **merge commit** (history shows the phase) |
| Feature | `feat/fixed-chunker` | hours to a day | the phase branch | PR, **squash** (one tidy commit per step) |
| Fix | `fix/overlap-loop` | hours | the phase branch | PR, squash |
| Experiment | `exp/semantic-400` | until the eval says yes or no | phase branch if kept; deleted if not | PR or delete |
| Docs | `docs/user-guide` | hours | phase branch or `main` | PR |

**Why squash for features:** your feature branch may have 9 messy commits ("wip", "typo").
Squash turns them into one clean commit: `phase1: add fixed-size chunker with tests`.
**Why a merge commit for phases:** the history then shows one visible "Phase 1 merged here"
point, which is what you point at in an interview.

---

## 4. The daily loop for one step (copy this)

```powershell
# 1. start from the latest phase branch
git checkout phase-1-baseline
git pull

# 2. make a small branch for this step
git checkout -b feat/fixed-chunker

# 3. work, test, commit (small commits are fine here)
pytest -q
ruff check .
git add src/docpilot/chunker.py tests/test_chunker.py
git commit -m "phase1: add fixed-size chunker with overlap"

# 4. push the branch to GitHub
git push -u origin feat/fixed-chunker

# 5. open a pull request (website, or the GitHub CLI below)
gh pr create --base phase-1-baseline --title "phase1: fixed-size chunker" --body-file .github/pull_request_template.md

# 6. wait for green CI; read your own diff on GitHub like a reviewer would; merge (squash)
gh pr merge --squash --delete-branch

# 7. back to the phase branch, ready for the next step
git checkout phase-1-baseline
git pull
```

At the phase gate: open a PR `phase-1-baseline -> main`, CI must be green, merge with a merge
commit, then tag `main` (section 7).

---

## 5. Pull request description template

We add `.github/pull_request_template.md` so every PR answers the same questions:

```markdown
## What changed
## Why (link the plan step / decision id)
## How I tested it (commands + output summary)
## Eval impact (real numbers, or "no retrieval change")
## Checklist
- [ ] tests pass   - [ ] ruff clean   - [ ] no file > 500 lines   - [ ] no secrets
```

Even when you are the only reviewer, writing this makes you re-read your own change. Hiring
managers do open PRs on portfolio repos; a clean PR history is visible proof of how you work.

---

## 6. Branch protection

**Rules we set on `main`** (and later on the current phase branch):

| Rule | Why |
|---|---|
| Require a pull request before merging | No accidental direct pushes |
| Require status checks to pass (`ci / test`, later `ci / eval-gate`) | Broken code or worse retrieval cannot enter |
| Require branches to be up to date before merging | Checks run against the latest `main` |
| Block force pushes | History cannot be rewritten |
| Block deletion | `main` cannot vanish |

**Important cost fact (VERIFY on GitHub docs on the day):** branch protection is free for
**public** repositories on GitHub Free; private repositories need a paid plan. A portfolio
repo should be public anyway. Before making it public: check `git log` contains no secrets
(Rule 6). GitHub Actions minutes are also free for public repositories (VERIFY current terms).

**How (GitHub website):** repository -> Settings -> Branches (or "Rules / Rulesets") ->
add a rule for `main`. The menu names change from time to time: follow current GitHub docs.

---

## 7. Tags: one per phase

```powershell
git checkout main
git pull
git tag -a phase-1 -m "Phase 1 gate: C0 recorded, mini API, golden v0"
git push origin phase-1          # tags are NOT pushed by a normal git push
git tag --list                   # see all tags
```

`-a` makes an **annotated** tag: it stores who, when, and a message. Lightweight tags (no
`-a`) are just names. For milestones, use annotated.

**Why tags matter here:** every eval result records a git commit. A tag lets you, an
interviewer, or CI check out exactly "the system as it was at Phase 3" and re-run the eval.

---

## 8. What CI checks, and when it grows

| From | CI job | Blocks merge when |
|---|---|---|
| Phase 1 (step 1f) | `test`: ruff lint + format check, pytest, 500-line check | any test fails, lint fails, a file > 500 lines |
| Phase 2 (step 2.10) | `eval-gate`: retrieval eval on a small committed fixture corpus | Recall@5 or MRR < baseline - tolerance |
| Phase 7 | `audit` (pip-audit), image build, deploy to AWS | known vulnerable package; build fails |

---

## 9. Mistakes and how to recover

| Situation | Fix |
|---|---|
| Committed on the wrong branch (not pushed) | `git switch -c feat/right-name` (your commits come along), then reset the old branch carefully, or ask the mentor first |
| Merge conflict | Open the file, keep the right lines between `<<<<<<<` and `>>>>>>>`, delete the markers, `git add`, `git commit` |
| Committed a secret | **Revoke the key at the provider first.** Then clean history. Deleting the file in a new commit is not enough |
| CI red on your PR | Read the job log, reproduce locally (`pytest -q`, `ruff check .`), fix, push again: the PR updates itself |
| Want to undo a pushed commit on a shared branch | `git revert <id>` (makes a new "undo" commit). Never rewrite shared history |

---

## 10. Self-check

1. Explain branch, PR, CI, branch protection, and tag with the book analogy.
2. Why squash feature PRs but merge-commit phase PRs?
3. Which checks block a merge in Phase 1? In Phase 2?
4. Why are tags pushed separately, and why annotated?
5. Why must the repo be public for free branch protection, and what do you check first?
6. You committed `.env` and pushed it. What is the very first thing you do?

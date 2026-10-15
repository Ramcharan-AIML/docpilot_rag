# DocPilot User Guide: What I Did, Step by Step

This guide is the **story of the project**, written so that months from now you can open it
and know exactly what was done, in what order, why, and with what results.
It covers everything from the first planning session up to **Step 0.4 (2026-10-08)**.
Add a new section each time a step or phase finishes.

- Detailed plans for future steps live in `docs/implementation_plan/`.
- Concepts explained simply live in `docs/teaching/`.
- The live status board is `docs/progress.md`.
- This guide connects them into one readable timeline.

---

## 1. DocPilot in five lines

1. **What:** an assistant that answers questions about technical docs (FastAPI, Docker,
   Pydantic, Qdrant, LangGraph, Redis) **with citations**.
2. **How:** RAG = first *find* the right doc pieces, then let an LLM *write* the answer from them.
3. **Extras:** hybrid search, reranking, agents, a human reviewer, guardrails, MLflow
   experiment tracking, RAG monitoring, and a cloud deployment on AWS (Terraform, k3s),
   later moved to Oracle.
4. **Proof:** every feature must win on measured evals, recorded in an ablation table.
5. **Constraint:** everything free, runs on a CPU laptop (32 GB RAM, Windows 11). AWS is used
   only on its free plan (credits, 6 months), then the demo moves to Oracle Always Free.

**The one rule behind everything:**
> Build the simplest version, measure it, change one thing, measure again, keep it only if
> the number says so.

---

## 2. What is in the repo right now

```text
docpilot_rag/
├── .env.example              settings template (empty keys); real .env is gitignored
├── .gitignore                keeps secrets, downloaded docs, models, vector data out of git
├── pyproject.toml            package settings: name, Python >=3.12, src layout, ruff, pytest
├── requirements.txt          runtime packages (pinned): sentence-transformers, numpy
├── requirements-dev.txt      runtime + tools (pinned): pytest, ruff
├── requirements-lock.txt     generated: all 46 installed packages, exact versions
├── README.md                 (one line now; full README in Phase 7)
├── CLAUDE.md                 rules Claude Code reads automatically every session
├── src/docpilot/__init__.py  makes "docpilot" an importable package (empty for now)
├── labs/
│   ├── lab1_embeddings.py           Step 0.3: embeddings + cosine similarity
│   └── lab2_keyword_vs_meaning.py   Step 0.4: keyword vs meaning search
├── scripts/  tests/  evals/golden/  evals/results/  data/docs/   (empty, hold .gitkeep)
├── .venv/                    private Python 3.13.2 (gitignored)
└── docs/                     all documentation (see section 3)
```

---

## 3. The documentation system (where to look for what)

| Question | File |
|---|---|
| Where am I? What is next? | `docs/progress.md` |
| What is the whole story so far? | `docs/USER_GUIDE.md` (this file) |
| What are the rules? | `docs/RULEBOOK.md` |
| What is the scope and the target? | `docs/PROJECT_DOCUMENTATION.md` (source of truth) |
| How will the finished system look? | `docs/architecture/architecture.md` + `2_architecture.md` |
| What exactly do I build next? | `docs/implementation_plan/phase_N_*.md` |
| Why does this concept work? | `docs/teaching/phase_N_*.md` |
| I know nothing about X: start from zero | `docs/teaching/primer_*.md` (evals, guardrails, Git, MLflow, storage, AWS, Terraform, Kubernetes, monitoring) |
| What will interviewers ask? | `docs/interview/phase_N_interview.md` |
| My own interview answers | `docs/interview_notes.md` |
| Why did we choose X and not Y? | `docs/decisions.md` |
| Context for a new chat | `docs/CHAT_CONTEXT.md` |

**The 500-line rule:** no file we write goes past 500 lines. Markdown continues in
`2_<name>.md`. Python files are split by responsibility instead, because Python cannot
import a module whose name starts with a digit.

---

## 4. The full road ahead

```text
Phase 0  Foundations ............ embeddings, setup                               <- YOU ARE HERE
Phase 1  Naive baseline ......... simplest RAG + evals + mini API + PRs/CI         -> C0 numbers
Phase 2  Chunking ............... clean data, 6 strategies, MLflow, CI eval gate   -> C1-C5
Phase 3  Retrieval .............. Docker, SeaweedFS/boto3, hybrid, reranker, judges -> C6-C8
Phase 4  Agents ................. LangGraph: route, grade, rewrite, check         -> C9
Phase 5  Multi-agent + HITL ..... tools, supervisor, human review, MCP            -> C10
Phase 6  Guardrails ............. injection, PII, red-team set                    -> C11 + safety table
Phase 7  Production ............. API, Redis, tracing, RAG monitoring, Docker,
                                  CI/CD -> AWS via Terraform, k3s, EKS exercise    -> public URL
         (month 5 of AWS plan) .. move to Oracle Always Free with the same setup
Phase 8  Stretch ................ GraphRAG-lite, DSPy, ColBERT (optional)
```

Every phase ends with a **gate**: tests pass, eval numbers recorded, decisions logged,
interview notes written in your own words, `progress.md` updated, git tag `phase-N`.
Estimated total: 10 to 12 weeks at about 5 hours a day (2 weeks added for the cloud work).

---

## 5. Session 1 (2026-10-03): planning

**What happened**
1. Read `PROJECT_DOCUMENTATION.md` completely.
2. Found a mismatch: section 18 says Phase 0 and Phase 1a code exist, but the repo had only
   `README.md` and `docs/`. Decision in practice: we rebuilt Phase 0 here.
3. Created the documentation system: rule book, progress, decisions, architecture
   (2 parts), implementation plan (all phases), teaching notes (all phases), interview Q&A
   (all phases), interview notes template.

**Open questions raised (still unanswered)**
- Is the old Phase 1a code somewhere else? (We are rebuilding, so this matters less now.)
- Phase 2 gate says "C1 to C6", but the ablation table defines C6 as hybrid (Phase 3).
  The plan follows the table (C1 to C5 in Phase 2). Needs your confirmation.
- D-014: generation evals (faithfulness etc.) placed at step 3.9. Needs your confirmation.

---

## 6. Git setup: branches and merging

**Branch names chosen** (one branch per phase, Rule 12):
`docs/project-plan`, `phase-0-foundations`, `phase-1-baseline`, `phase-2-chunking`,
`phase-3-hybrid-retrieval`, `phase-4-langgraph-agents`, `phase-5-tools-hitl-mcp`,
`phase-6-guardrails`, `phase-7-production`. Small work inside a phase uses prefixes
`feat/`, `fix/`, `exp/` (experiments you may throw away), `docs/`.

**What you ran**
```powershell
git checkout -b docs/project-plan
git add docs/
git commit -m "docs: add rule book, architecture, phase plans, teaching notes, interview Q&A"
git checkout main
git merge --no-ff docs/project-plan -m "Merge branch 'docs/project-plan'"
git checkout -b phase-0-foundations
```

**Why `--no-ff`:** it always creates a merge commit, so history shows where each branch
came in. Without it, git may "fast-forward" and the branch leaves no trace.
**Better habit from now on:** push the branch and merge through a GitHub pull request.
From Phase 7 the CI eval gate runs on pull requests.

---

## 7. Step 0.1: project skeleton (2026-10-03, commit `497a9a4`)

**Goal:** folders and safety files exist before any code.

**Files created:** `.gitignore`, `.env.example`, `src/docpilot/__init__.py`, and an empty
`.gitkeep` in `labs/`, `scripts/`, `tests/`, `evals/golden/`, `evals/results/`, `data/docs/`.

**Why each one**
- `.gitignore`: secrets (`.env`), downloaded docs (licenses), models, vector and database
  files, caches, `.venv/` must never reach git. Bots scan GitHub for leaked keys within minutes.
- `.env.example`: shows which settings exist, with empty values. Added `LLM_MODEL`, because
  the Phase 1 `config.py` reads it.
- `.gitkeep`: **git does not track empty folders**. A tiny placeholder keeps them.

**Two lessons worth remembering**
1. `data/docs/` (with a slash) ignores the whole folder and a `!` exception cannot reach
   inside it. `data/docs/*` ignores only the contents, so `!data/docs/.gitkeep` works.
2. `.env.*` + `!.env.example` also blocks files like `.env.local` and `.env.prod`.

**How it was checked**
```powershell
git check-ignore -v .env                    # shows which .gitignore line ignores it
git check-ignore -v data/docs/fake_page.md  # downloaded docs are ignored too
```
A fake `.env` and a fake doc both stayed invisible to `git status`. Test files deleted after.

---

## 8. Step 0.2: virtual environment and pinned packages (2026-10-03, commit `497a9a4`)

**Goal:** one private Python for this project, with exact package versions.

**What we found and decided**
- Your Python is **3.13.2**; a clean `.venv` already existed, so we reused it.
- Versions were checked on PyPI on build day (Rule 4: never trust memory for versions).
- **numpy 2.5.3 requires Python 3.12+**, so the project needs `>=3.12`, not the 3.11+ written
  in `PROJECT_DOCUMENTATION.md` (decision **D-015**). The Phase 7 Dockerfile and CI in the
  plan were changed to Python 3.13 so laptop, CI, and server match.
- Three requirement files (decision **D-016**):

| File | Holds | Why |
|---|---|---|
| `requirements.txt` | sentence-transformers 6.1.0, numpy 2.5.3 | what the product needs |
| `requirements-dev.txt` | `-r requirements.txt` + pytest 9.1.1, ruff 0.16.10 | tools never go into production images |
| `requirements-lock.txt` | all 46 packages, exact versions | reproducible installs |

**Commands**
```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pip install -e .                       # editable install of src/docpilot
python -c "import docpilot; print('ok')"
```

**Checks that passed:** `import docpilot` works from another folder; torch is
`2.14.1+cpu` (CPU build, CUDA not available, as expected); `pip check` clean; ruff clean.

**Why a lock file (in one paragraph):** `requirements.txt` pins only the 2 packages you
chose, but they pull in 44 more, declared as **ranges** (for example `torch>=2.2`). pip
installs the newest version in each range *on install day*, so the same `requirements.txt`
can give a different torch next month, and your eval numbers could change with no code
change. The lock file records the exact full set that was tested. Rebuild it exactly with
`pip install -r requirements-lock.txt`.

**Mistake caught along the way:** the plan's Dockerfile sketch had comments on the same line
as `FROM`. Docker does not allow that; it was fixed in the plan.

---

## 9. Step 0.3: Lab 1, embeddings and cosine similarity (2026-10-07, commit `5924b95`)

**Goal:** see with your own eyes that similar meaning gives similar vectors.

**Model card checked first** (recorded in decision D-002):

| Fact | Value | Why it matters |
|---|---|---|
| Vector size | 384 | Every text becomes 384 numbers |
| Max input | 512 tokens | Longer text is cut off **silently** (Phase 2 chunk sizes) |
| Query prefix | `Represent this sentence for searching relevant passages: ` | Questions only |
| License | MIT | Free to use |
| Last module | `Normalize` | Vectors already have length 1, so cosine = dot product |
| Revision | `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` | Pinned, like the lock file |

**File:** `labs/lab1_embeddings.py`: encodes 3 sentences, prints vector size, first numbers,
vector length, and a hand-written cosine similarity for every pair.

**Your predictions:** highest = question vs Pydantic sentence; lowest = a cat pair;
length = 1.0. **All correct.**

**Your real results**

| Pair | Cosine |
|---|---|
| "How do I validate incoming request data?" vs "Pydantic models check the request body for you." | **0.708** |
| validate question vs "My cat likes to sleep in the sun." | 0.379 |
| Pydantic sentence vs cat sentence | 0.388 |
| Length of vector 0 | 1.0 |

**Break-it run** (sentence 2 changed to "Make sure the data a client sends is correct."):
question vs paraphrase **0.799**, question vs cat 0.379 (same two sentences, same score),
paraphrase vs cat 0.410. File restored to the original afterwards.

**Lessons**
1. Unrelated sentences still scored about 0.38, not 0. **Scores are for ranking only**,
   never percentages.
2. 0.379 vs 0.388 is a tie. Tiny gaps are noise, not winners.
3. A *reworded question* (0.799) scored higher than the *answer* (0.708). Search wants
   answers, which is why BGE uses a query prefix for questions.
4. Honest note: the paraphrase still shared the word "data", so it was not a perfect
   zero-shared-words test. Change one thing at a time.
5. Floating point: the cosine of identical directions printed 0.9999999999999998, not 1.0.
   Compare scores with a tolerance, never with `==`.

---

## 10. Step 0.4: Lab 2, keyword vs meaning search (2026-10-08, not yet committed)

**Goal:** discover that each kind of search fails in a different place. This is the reason
hybrid search exists (Phase 3).

**File:** `labs/lab2_keyword_vs_meaning.py`. Changes from the plan's sketch:
- Words are split with a regular expression, so punctuation does not block matches
  (`Dockerfile.` becomes `dockerfile`) and `max_length` stays one word.
- A "picks" line shows each method's winner, or **NOTHING** when all scores tie.
- An extra column shows meaning scores **without** the BGE query prefix.

**Your predictions:** Q1: keyword doc 1, meaning doc 1. Q2: keyword no match, meaning doc 2.
**All four correct.** (No prediction for the prefix question.)

**Your real results**

| Question | Document | keyword | meaning | meaning, no prefix |
|---|---|---|---|---|
| "what does max_length do" | 1 `Query(max_length=50)` | 1 | **0.742** | 0.775 |
| | 2 Pydantic validates body | 0 | 0.539 | 0.592 |
| | 3 Docker images | 0 | 0.490 | 0.534 |
| "how do I check incoming data is correct" | 1 `Query(max_length=50)` | 0 | 0.578 | 0.564 |
| | 2 Pydantic validates body | 0 | **0.659** | 0.670 |
| | 3 Docker images | 0 | 0.502 | 0.529 |

Picks: Q1 keyword doc 1, meaning doc 1. Q2 keyword **NOTHING**, meaning doc 2.

**Lessons**
1. **Keyword search failed Q2 completely**: the question shares zero words with every
   document, so it cannot rank anything. Meaning search still found the Pydantic document.
2. Meaning search won Q2 by a smaller margin (0.659 vs 0.578) than Q1 (0.742 vs 0.539).
   Paraphrases are harder, even for meaning search.
3. **The prefix:** it lowered 5 of 6 scores and changed no winner. It widened the gap on Q1
   (0.203 vs 0.183) and narrowed it on Q2 (0.081 vs 0.106). Two questions cannot settle
   whether the prefix helps; that is a job for the Phase 1 eval set with many questions.
4. **Honest limit:** this lab did not show meaning search *failing*. Both methods won Q1.
   Meaning search is known to be weak on near-identical names (for example `max_length`
   vs `min_length`); we will see real evidence in the Phase 3 per-type evals.

**Still to do for Step 0.4:** write two sentences in your own words in `docs/progress.md`:
which method got each question right, and why the other failed.

---

## 10b. Step 1a.1: `config.py`, all settings in one place (2026-10-09, not yet committed)

**Goal:** one file holds every setting (paths, model, chunk size, top-k, LLM provider), so an
experiment changes one line. Secrets stay in `.env` (gitignored).

**Files:** `src/docpilot/config.py` (new), `requirements.txt` + lock (`python-dotenv==1.2.4`),
`docs/decisions.md` (D-026).

**Key lines:**
- `PROJECT_ROOT = Path(__file__).resolve().parents[2]`: paths are built from where the file
  lives, not from the folder you run Python in.
- `load_dotenv(PROJECT_ROOT / ".env")`: copies `.env` into `os.environ`; never overwrites a
  variable that is already set.
- `EMBEDDING_REVISION`: pinned model files (the plan forgot this; fixed openly).
- `NOT_FOUND_PHRASE`: one copy, used by the prompt now and by the evals later.

**Check and real result:**
```powershell
python -c "from docpilot import config; print(config.DOCS_DIR)"
# C:\Users\rajes\OneDrive\Desktop\1\AIML\9_DOCPILOT_RAG_BASED\docpilot_rag\data\docs
```

**Lessons:** (1) `print(path)` shows only the path, no label: that single line *is* the
output. (2) Importing `config` does not check that the folder exists or has files; it only
builds a path. (3) No prediction was written before the run: write one next time.

---

## 10c. Step 1a.2: `loader.py`, files into Documents (2026-10-10, not yet committed)

**Goal:** read every `.md`/`.txt` under `data/docs/` into `Document(text, source)`, in the
same order on every machine. **Files:** `src/docpilot/loader.py`, `tests/test_loader.py`.

**Plan bugs fixed:** missing folder returned `[]` silently (now `FileNotFoundError`); a
folder named `x.md` crashed `read_text` (now `is_file()`); `sorted(Path)` differs between
Windows and Linux (now sort by the `source` string).

**Real results:**
| Run | You predicted | Real |
|---|---|---|
| real `data/docs` (only `.gitkeep`) | error | `[]` (no error) |
| `no_such_folder` | `FileNotFoundError`, line 19 | `FileNotFoundError`, line 19 |
| `pytest tests/test_loader.py -v` | n/a | 4 passed |

**Lessons:** "folder is missing" (a mistake: stop) and "folder is empty" (a fact: let the
caller decide) are different cases. A traceback is read bottom-up: the last line is the
error, the line above it is where it was raised.

---

## 11. Where we are right now (2026-10-08)

| Item | Status |
|---|---|
| Branch | `phase-0-foundations` |
| Steps 0.1, 0.2, 0.3 | done and committed |
| Step 0.4 | run done; your two sentences pending; lab file not committed yet |
| Interview notes | you added Phase 0 questions 3 and 4; answers still to write |
| Phase 0 gate | not started |

**To commit the current work**
```powershell
git add labs/lab2_keyword_vs_meaning.py docs/ CLAUDE.md
git commit -m "phase0: lab 2 keyword vs meaning, user guide, CLAUDE.md, chat context"
```

---

## 11b. Scope change v1.1 (2026-10-08): new technologies

**What you asked for:** AWS (EC2, S3, ECR, IAM, CloudWatch, VPC) as the main deployment target
on the free plan; Terraform; MinIO + boto3; k3s planned; EKS as a short exercise; MLflow from
Phase 2; RAG monitoring; a stronger Git workflow; and child-level teaching of evals and
guardrails.

**What we checked on the web first (Rule 4), and what it changed**

| Finding (2026-10-08) | Consequence |
|---|---|
| AWS free plan: USD 100 + up to 100 credits, max 6 months, then suspension and deletion | Account created at the **start of Phase 7** (your choice); move to **Oracle** before month 6 (your choice) |
| Server time is paid from credits; the free plan cannot bill beyond them | Credits treated as a budget: Rule 17 (cost safety) |
| EKS control plane USD 0.10/hour, no free tier | EKS = `terraform plan` by default; any apply destroyed in the same sitting |
| Public IPv4 USD 0.005/hour | One address only |
| MinIO community edition archived (Apr 2026), images and binaries removed (Sep 2026) | **SeaweedFS** replaces it (your choice); boto3 code unchanged |
| MLflow 3 also does GenAI tracing | MLflow becomes a third candidate for the tracing decision (D-009) |
| Terraform is BSL; OpenTofu is the open-source fork | Plain HCL that runs on both |
| k3s needs about 2 GB RAM for a server node | Fits on `m7i-flex.large` (verify) after measuring our stack |

**Where each new thing lives**

| Topic | Primer | Plan steps |
|---|---|---|
| Evals from zero | `teaching/primer_evals.md` | 1c-1d, 3.9, 4.5, 5.7, 6.1 |
| Guardrails from zero | `teaching/primer_guardrails.md` | 6.1-6.8 |
| Git workflow | `teaching/primer_git_workflow.md` | 1f, 2.10 |
| MLflow | `teaching/primer_mlflow.md` | 2.0, 3.1b |
| SeaweedFS + boto3 | `teaching/primer_object_storage.md` | 3.1b |
| RAG monitoring | `teaching/primer_rag_monitoring.md` | 7.7 |
| AWS | `teaching/primer_aws.md`, `2_primer_aws.md` | 7.10-7.13 |
| Terraform | `teaching/primer_terraform.md` | 7.11-7.12, 7.15, 7.18 |
| Kubernetes (k3s, EKS) | `teaching/primer_kubernetes.md` | 7.14-7.15 |

Also new: `architecture/3_architecture.md` (cloud, IAM, secrets, storage, Kubernetes,
pipeline, MLOps loop, portability, costs), Phase 7 plan in four parts, decisions D-017 to
D-025, Rule 17, and `PROJECT_DOCUMENTATION.md` v1.1.

---

## 12. What comes next

**Phase 0 gate** (from `implementation_plan/phase_0_foundations.md`)
- [x] skeleton committed; `.env` proven ignored
- [x] venv works; editable install works; versions pinned and recorded
- [ ] lab 1 and lab 2 run and explained in your own words (Lab 2 sentences pending)
- [x] D-002 has a "verified on" date for the model card
- [ ] Phase 0 interview notes written in your own words
- [ ] merge `phase-0-foundations` into `main`, then `git tag phase-0`

**Phase 1 preview** (`implementation_plan/phase_1_baseline.md`, branch `phase-1-baseline`)

```text
01_download_docs.py ─▶ data/docs/fastapi/*.md
02_ingest.py:  loader ─▶ chunker (800 chars, 100 overlap) ─▶ embedder ─▶ Qdrant (docpilot_naive)
03_ask.py:     question ─▶ embed with prefix ─▶ top 4 chunks ─▶ prompt ─▶ LLM ─▶ answer + [n] citations
```

| Step | File(s) | What you will learn |
|---|---|---|
| 1a.1 | `src/docpilot/config.py` | all settings in one place, secrets from `.env` |
| 1a.2 | `loader.py` + test | files to `Document` objects |
| 1a.3 | `chunker.py` + 5 tests | fixed-size chunks with overlap |
| 1a.4 | `embedder.py` | load the model once, prefix only on questions |
| 1a.5 | `vector_store.py` | Qdrant local mode, stable ids, search |
| 1a.6 | `llm.py` | one OpenAI-compatible client for free providers |
| 1a.7 | `rag.py` | the whole pipeline in one function |
| 1a.8 | `scripts/01..03` | download, ingest, ask |
| 1b | `docs/failure_log_phase1.md` | read failures before measuring |
| 1c | `evals/golden/dev.jsonl`, `test.jsonl` | the answer key (about 30 questions) |
| 1d | `evals/metrics.py`, `matching.py`, `run_retrieval_eval.py` | Recall@k, MRR, nDCG; record **C0** |
| 1e | `src/docpilot/api.py` + tests | FastAPI `POST /ask` |
| 1f | `.github/workflows/ci.yml`, PR template, branch protection | PRs, CI, protected `main` (start using PRs at 1a.1) |

Before Phase 1 you will need a **free LLM API key** (Groq first). We check current free
models and limits on build day and record them in `decisions.md`.

---

## 13. Daily commands

```powershell
.venv\Scripts\Activate.ps1                  # every new terminal
git status                                  # before every commit: read the list
python labs/lab1_embeddings.py              # rerun a lab
pytest -q                                   # tests (from Phase 1)
ruff check . ; ruff format .                # lint and format
git log --oneline --graph -10               # see history
```

---

## 14. Concepts you have learned so far

| Concept | One line |
|---|---|
| Embedding | a list of numbers (384 here) that places a text on a "meaning map" |
| Cosine similarity | how much two vectors point the same way; for ranking, not a percentage |
| Normalisation | vectors of length 1, so cosine = dot product |
| Tokens and the 512 limit | models read word pieces; text past the limit is cut silently |
| Query prefix | BGE adds an instruction to questions only, so questions land near answers |
| Keyword vs meaning search | keyword needs shared words; meaning handles paraphrases |
| Virtual environment | a private Python per project |
| Pinning and lock files | exact versions, including hidden dependencies, so results repeat |
| Editable install | `pip install -e .` makes `src/docpilot` importable everywhere |
| `.gitignore` / `.gitkeep` | keep secrets out; keep empty folders in |
| `--no-ff` merge | keeps a visible merge commit per branch |
| Predict before you run | the habit that turns runs into learning |
| Settings vs secrets | settings in `config.py` (in git); secrets in `.env` (never in git) |
| `load_dotenv` | copies `.env` into environment variables; real env vars win |

---

## 15. Keeping this guide up to date

At the end of each step, add a section like 7 to 10 above: goal, files, commands, checks,
**your real numbers**, lessons. Update section 11 (where we are). When a part passes 500
lines, continue in `2_USER_GUIDE.md`. **Part 2 started 2026-10-12 (step 1a.3 onward):**
[2_USER_GUIDE.md](2_USER_GUIDE.md).

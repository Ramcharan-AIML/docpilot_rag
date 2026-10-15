Continues from [phase_1_baseline.md](phase_1_baseline.md)

# Phase 1: Naive Baseline, Eval Harness, Mini API (Part 2 of 2)

---

## Step 1b: Run it and inspect failures

**Goal:** see naive RAG fail with your own eyes, before measuring anything.

**File:** `docs/failure_log_phase1.md`

Ask 10 questions with `03_ask.py`, mixing question types from `PROJECT_DOCUMENTATION.md`
section 2 (factual, how-to, exact identifier, paraphrase, comparison, code, not-in-docs).
For each one, fill a row:

| # | Question | Type | Answer correct? | Right chunk in top 4? | What went wrong (your words) |
|---|---|---|---|---|---|
| 1 | ... | how-to | yes/no | yes/no, rank | e.g. "chunk had `{* ... *}` marker, not the code" |

Then write three lines: the most common failure, the most surprising one, and which
Phase 2/3 feature you think would fix it. These three lines are gold in an interview.

Known failures to look for (section 18.3): missing code (include markers), chunks cut mid
structure, HTML noise inside chunks.

---

## Step 1c: Golden dataset v0

**Goal:** an answer key, so "better" becomes a number.

**Files:** `evals/golden/dev.jsonl`, `evals/golden/test.jsonl`, `evals/golden/README.md`

Rules:

1. About 30 questions to start. Reuse the 10 from step 1b, add 20 new ones.
2. Cover every type in section 2 at least once; mark the type in `type`.
3. About 15% unanswerable (`should_answer: false`, `evidence: []`).
4. Evidence = document + **verbatim snippet** copied from the raw doc (D-010). Keep
   snippets short (one sentence or one line of code) so they survive chunking.
5. Split about 70% dev and 30% test, balanced by type. Test is only run at gates.
6. Write every item by hand; read each snippet back against the file.

```json
{"id": "q-001", "question": "How do I make a query parameter optional?", "type": "how-to", "should_answer": true, "reference_answer": "Give it a default value of None.", "evidence": [{"doc": "fastapi/query-params.md", "snippet": "short verbatim text copied from the doc"}], "difficulty": "easy", "split": "dev", "notes": ""}
```

**Validation script:** `evals/validate_golden.py` checks every line parses, ids are unique,
required fields exist, and **every snippet really appears in its doc**. Run it after every
edit. A typo in a snippet silently turns a hit into a miss, so this check matters.

---

## Step 1d: Retrieval eval harness and C0

**Goal:** a script that prints Recall@k, MRR, nDCG@k for any collection.

### 1d.1 `evals/matching.py`: is a chunk a hit?

```python
"""Decide whether a retrieved chunk contains a gold evidence snippet."""
from difflib import SequenceMatcher


def normalise(text: str) -> str:
    """Lowercase and squash all whitespace, so line breaks do not cause misses."""
    return " ".join(text.lower().split())


def snippet_in_chunk(snippet: str, chunk_text: str, min_overlap: float = 0.7) -> bool:
    """True if the snippet is inside the chunk, or most of it is.

    The 'most of it' part handles a snippet cut in half by a chunk boundary.
    min_overlap is a setting we record with every result.
    """
    snippet_n, chunk_n = normalise(snippet), normalise(chunk_text)
    if snippet_n in chunk_n:
        return True
    matcher = SequenceMatcher(None, snippet_n, chunk_n, autojunk=False)
    match = matcher.find_longest_match(0, len(snippet_n), 0, len(chunk_n))
    return match.size / max(len(snippet_n), 1) >= min_overlap


def relevance_list(retrieved: list[dict], evidence: list[dict]) -> list[int]:
    """One 0/1 per retrieved chunk. Each gold snippet is counted once only,
    so overlapping chunks that repeat the same snippet do not inflate scores."""
    found = set()
    relevance = []
    for hit in retrieved:
        is_relevant = 0
        for index, item in enumerate(evidence):
            if index in found or hit["source"] != item["doc"]:
                continue
            if snippet_in_chunk(item["snippet"], hit["text"]):
                found.add(index)
                is_relevant = 1
                break
        relevance.append(is_relevant)
    return relevance
```

### 1d.2 `evals/metrics.py`: pure functions, written by hand

```python
"""Retrieval metrics. Input: a 0/1 relevance list in rank order."""
import math


def recall_at_k(relevance: list[int], k: int) -> float:
    """Hit rate: 1.0 if any relevant chunk is in the top k, else 0.0."""
    return 1.0 if any(relevance[:k]) else 0.0


def strict_recall_at_k(relevance: list[int], k: int, num_evidence: int) -> float:
    """Share of gold snippets found in the top k (for multi-evidence questions)."""
    return sum(relevance[:k]) / num_evidence if num_evidence else 0.0


def reciprocal_rank(relevance: list[int]) -> float:
    """1 / rank of the first relevant chunk; 0 if none. Averaged over questions = MRR."""
    for rank, is_relevant in enumerate(relevance, start=1):
        if is_relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(relevance: list[int], k: int, num_evidence: int) -> float:
    """Rewards relevant chunks near the top. log2(rank + 1) is the 'discount'."""
    dcg = 0.0
    for rank, is_relevant in enumerate(relevance[:k], start=1):
        dcg += is_relevant / math.log2(rank + 1)
    ideal_hits = min(num_evidence, k)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / ideal if ideal > 0 else 0.0
```

**Tests:** `tests/test_metrics.py` with hand-computed cases, for example relevance
`[0, 1, 0, 0]` gives reciprocal rank `0.5` and recall@1 `0.0`, recall@2 `1.0`. Work these
out on paper first, then let the test confirm. These numbers are maths facts about the
formulas, not project results.

### 1d.3 `evals/run_retrieval_eval.py`

```text
usage: python evals/run_retrieval_eval.py --collection docpilot_naive --split dev --config-id C0

for each golden item with should_answer == true:
    hits      = search(collection, embed_query(question), top_k=10)   # 10 so we can report @1,@3,@5
    relevance = relevance_list(hits, item["evidence"])
    record recall@1/3/5, strict recall@5, reciprocal rank, nDCG@5, search latency (ms)

aggregate: mean over all items, AND mean per question type
save: evals/results/<date>_<config-id>_<split>.json
print: a small table
```

**Latency baseline L0 (D-031, `teaching/primer_latency.md`):** a second small script,
`evals/run_latency.py`, runs the full `ask()` (embed, search, LLM) on the dev questions
after **one warm-up call**, collects `timings_ms` per stage, and reports p50 and p95 per
stage and total, with n, hardware ("laptop CPU") and provider/model. Sleep between calls
to respect the free-tier rate limit; record any 429 retries (they are part of the tail).
Saved next to the retrieval JSON; the ABLATION row C0 gets `p50 total` and `p95 total`.

Each result JSON stores: `config_id`, `collection`, `split`, `date`, `git_commit`
(from `git rev-parse --short HEAD`), `settings` (chunk size, overlap, model, top_k,
min_overlap), `overall`, `per_type`, and `per_question` (so failures can be inspected).

### 1d.4 Abstention check (deterministic, no judge)

`evals/run_abstention_check.py`: for every item, run `rag.ask`, then check
`NOT_FOUND_PHRASE in answer`. Abstention accuracy = share of items where
"said not found" equals `not should_answer`. This uses LLM tokens (one call per question),
so it is run by hand, not in CI.

### 1d.5 `evals/ABLATION.md`

Copy the template from `PROJECT_DOCUMENTATION.md` section 14.7. Fill only the C0 retrieval
columns from the real result JSON. Everything else stays `n/a`.
In Phase 2 we write `evals/make_ablation.py` to generate this file from the JSON results.

**Done when:** the C0 row has real Recall@5, MRR, nDCG@5 on dev, with date and commit.

---

## Step 1e: Mini FastAPI wrapper

**Goal:** the same `ask()` behind `POST /ask`, with automatic docs at `/docs`.

New dependencies (decision log first): `fastapi`, `uvicorn`, `httpx` (for tests).

**Files:** `src/docpilot/api.py`, `tests/test_api.py`

```python
"""Mini API for Phase 1. Becomes the api/ package in Phase 7."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

from docpilot import config
from docpilot.llm import get_llm_client
from docpilot.rag import ask
from docpilot.vector_store import get_client


class AskRequest(BaseModel):
    # Pydantic rejects bad input with a 422 before our code runs
    question: str = Field(min_length=1, max_length=2000)


class Source(BaseModel):
    source: str
    chunk_number: int
    score: float


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at startup: open Qdrant and the LLM client, keep them on app.state
    app.state.qdrant = get_client(config.QDRANT_PATH)
    app.state.llm = get_llm_client()
    yield
    app.state.qdrant.close()  # runs once at shutdown


app = FastAPI(title="DocPilot", lifespan=lifespan)


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(request: AskRequest) -> AskResponse:
    # A plain `def` (not async): FastAPI runs it in a thread pool, so the slow
    # model and LLM calls do not freeze the server. Async comes in Phase 7.
    result = ask(request.question, app.state.qdrant, app.state.llm)
    return AskResponse(answer=result["answer"], sources=result["sources"])
```

**Run:** `uvicorn docpilot.api:app --reload`, then open `http://127.0.0.1:8000/docs` and
try the endpoint from the browser.

**Tests (`tests/test_api.py`):** use FastAPI's `TestClient` and replace `ask` with a fake
function (pytest `monkeypatch`), so the test needs no model and no API key:
1. valid question returns 200 and the fake answer
2. empty question returns 422
3. a 3000-character question returns 422

Note: local-mode Qdrant allows one process, so stop the API before running `02_ingest.py`.

---

## Step 1f: Git workflow, first CI, branch protection (decision D-024)

**Goal:** from now on nothing reaches `main` without a pull request and green checks.
Teaching: `docs/teaching/primer_git_workflow.md`.

**Note:** in practice, start using feature branches + PRs at the **beginning** of Phase 1
(step 1a.1), and set up this CI as soon as the first test exists (1a.3). It is listed here so
all Git work sits in one place.

1. **Make the repo public** (free branch protection and free Actions minutes for public
   repos; VERIFY current GitHub terms). First: `git log -p | Select-String -Pattern "API_KEY"`
   style check that no secret was ever committed.
2. **`.github/pull_request_template.md`**: What changed / Why (plan step, decision id) /
   How I tested / Eval impact (real numbers or "no retrieval change") / checklist.
3. **`scripts/check_file_lengths.py`**: lists tracked text files over 500 lines (Rule 1);
   exits with code 1 if any (except `docs/PROJECT_DOCUMENTATION.md`).
4. **`.github/workflows/ci.yml`**, job `test`:

```yaml
# VERIFY: current action versions on build day; pin them
name: ci
on:
  pull_request:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@vX
      - uses: actions/setup-python@vX
        with: {python-version: "3.13"}
      - run: pip install -r requirements-dev.txt && pip install -e .
      - run: ruff check . && ruff format --check .
      - run: pytest -q                      # tests never call a real LLM or download docs
      - run: python scripts/check_file_lengths.py
```

5. **Branch protection on `main`:** require PR, require status check `ci / test`, require
   up-to-date branch, block force-push and deletion.
6. **Prove it:** open a PR with a deliberately failing test; see the red cross and the
   disabled merge button; fix it; see green; merge. Screenshot both for the README.

**Done when:** a direct `git push origin main` is rejected, and a PR merges only when green.
The retrieval **eval gate** joins this workflow in Phase 2 step 2.10.

---

## Phase 1 gate

- [ ] `pytest` green: chunker, loader, metrics, matching, API tests
- [ ] `docs/failure_log_phase1.md` has 10 rows and the three summary lines
- [ ] golden v0 (about 30 items) passes `validate_golden.py`
- [ ] C0 retrieval row in `evals/ABLATION.md` with real numbers (dev); test split run once
- [ ] abstention accuracy for C0 recorded (or `n/a` with a reason)
- [ ] latency baseline L0: p50/p95 per stage and total, warm, n and hardware named (D-031)
- [ ] decisions: versions pinned for `qdrant-client`, `openai`, `python-dotenv`, `fastapi`,
      `uvicorn`, `httpx`; Groq (or chosen provider) model name and limits verified with date
- [ ] learner explains every module and every metric in `docs/interview_notes.md`
- [ ] CI `test` job green; branch protection on `main` proven (direct push rejected)
- [ ] phase branch merged into `main` through a PR; annotated tag `phase-1` pushed

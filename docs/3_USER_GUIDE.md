Continues from [2_USER_GUIDE.md](2_USER_GUIDE.md)

# DocPilot User Guide (part 3)

---

## 28. Phase 0 and Phase 1 gates closed (2026-10-15)

**What a gate is:** a checklist that must pass before the next phase starts. Like a school
year: you move up only after the final exam, so gaps do not pile up.

**Phase 1 gate, item by item:**
| Item | Result |
|---|---|
| Tests green | 62 passed, on Windows and on GitHub's Linux machine |
| Failure log | 10 rows + 3 summary lines |
| Golden set | 32 items, validator OK |
| C0 retrieval | dev: Recall@5 0.842, MRR 0.667, nDCG@5 0.670; test (run once): Recall@5 1.000, MRR 0.635 |
| Abstention | 0.909 (0/3 made-up answers, 2/19 wrong refusals) |
| Latency L0 | warm p50 1107 ms, p95 1764 ms (LLM about 96%) |
| Versions pinned | D-026 to D-035 |
| Interview notes | written as **mentor drafts** at your request: rewrite them in your own words |
| CI | green on PR #1; branch protection deferred until the repo is public (D-035) |
| Merge + tag | PR #1 merged into `main`; tags `phase-0` and `phase-1` |

**Honest note:** the gate asks for answers in your own words because interviews test you,
not the file. The drafts are a starting point: read one, close it, say it aloud, rewrite.

**What Phase 1 proved, in one breath:** the baseline finds the right chunk for most
questions but rarely ranks it first; the chunk text itself is broken (missing code, cut
sentences, HTML); the LLM refuses honestly; and the LLM is almost all of the waiting time.
Phase 2 fixes the chunk text and compares chunking strategies against C0.

---

## 29. Step 2.0: MLflow, the lab notebook (2026-10-15, not yet committed)

**Goal:** every eval run is recorded automatically and can be sorted and compared on a web
page. Like a scientist's lab notebook: recipe, result, and the photos stapled in.

**Files:** `evals/tracking.py`, `evals/relog_results_to_mlflow.py`,
`tests/test_tracking.py`; settings in `config.py`; decision D-036 (`mlflow==3.17.1`,
dev only).

| MLflow word | In DocPilot |
|---|---|
| experiment | `docpilot-retrieval`, `docpilot-latency`, `docpilot-abstention` |
| run | one saved result file, named by config id (C0) |
| params | the recipe: golden version, chunk strategy and size, model, split |
| metrics | the scores: recall_at_5, mrr, total_p50_ms, accuracy, ... |
| tags | config id, git commit, results file, ablation |
| artifact | the full results JSON |

**Why full MLflow, not mlflow-skinny:** skinny has no web UI and no SQLite storage.
**Why not W&B:** hosted, plan limits, data leaves the laptop.

**Run (hands-on):**
```powershell
python -m evals.relog_results_to_mlflow
mlflow ui --backend-store-uri sqlite:///mlflow.db
```
Then open `http://127.0.0.1:5000`. From now on every eval run is logged by itself.

**Real results:** smoke test (throwaway database): 4 C0 files logged, numbers equal to the
JSON, re-run skips duplicates. Your UI check (2026-10-15): both C0 retrieval runs visible
under Model training; Compare showed identical params except `split`, and the JSON values.

**PDF and Word (D-037):** step 2.7 now covers PDF, Word (DOCX) and HTML with Docling.

---

## 30. Step 2.1: reorganise the code into packages (2026-10-15, not yet committed)

**Goal:** make room for six chunkers and more loaders **without changing any behaviour**.
Like moving house: the furniture goes into labelled rooms, but nothing is thrown away or
rebuilt.

| Before (Phase 1) | After | Room for |
|---|---|---|
| `loader.py` | `ingestion/loader.py` | cleaner, includes, blocks, PDF/Word loader |
| `chunker.py` | `ingestion/chunkers/fixed.py` + `chunkers/base.py` (`Chunk`) | recursive, semantic, parent-child, ... |
| `embedder.py` | `embedding/dense.py` | sparse vectors (Phase 3) |
| `vector_store.py` | `store/qdrant_store.py` | Qdrant server mode (Phase 3) |
| `llm.py` | `llm/client.py` | provider fallback (Phase 7) |

**How:** `git mv` (git keeps each file's history), then every import updated; no
"compatibility" copies of old names, so nothing points to two places.

**How we know nothing changed:**
1. 66 tests pass (same tests, new import paths).
2. **Regression check by hand (your hands-on):** rebuild the index with the moved code and
   run the eval; the scores must equal C0 exactly. A refactor that changes a number is a bug.

**Run:**
```powershell
python scripts/02_ingest.py
python -m evals.run_retrieval_eval --split dev --config-id C0-2.1
```

**Real results (2026-10-15):** tests 66 passed. Regression check (commit `785120a`): every
metric and all 19 questions' retrieved chunks identical to C0; only search latency
moved (machine timing). **Passed.**

---

## 31. Step 2.2: the cleaner (2026-10-15, not yet committed)

**Goal:** remove HTML noise that changes embeddings but means nothing to a reader. Like
washing vegetables before cooking: same vegetables, no mud.

**Measure first:** 144 tags in the 4 pages; **114 inside ```console blocks** (the coloured
terminal screenshot), 30 in normal text; **none** inside python/JSON code.

**Plan bug found and fixed:** the plan's cleaner skipped every code fence, so it would have
left 114 of 144 tags. Our rule: normal text and `console` blocks are cleaned (a console
block is a picture of a terminal, not code you run); every other code block is never
touched.

| Input | Output |
|---|---|
| `<dfn title="...">conversion</dfn>` | `conversion` |
| `$ <font color="#4E9A06">uv run fastapi</font> dev` (console) | `$ uv run fastapi dev` |
| `html = "<span>x</span>"` inside ```python | unchanged |
| `<https://fastapi.tiangolo.com>` (a link) | unchanged |

**Result on the real pages:** tags 144 -> 0; characters 34350 -> 31720; all 30 real code
blocks byte-identical. 7 tests.

**Run (hands-on):**
```powershell
python scripts/02_ingest.py --clean --collection docpilot_clean
python -m evals.run_retrieval_eval --collection docpilot_clean --split dev --config-id C0+clean
```
**Real results:** n/a (your run, after a prediction).

---

## 32. Step 2.3: put the real code into the docs (2026-10-17, not yet committed)

**Goal:** the pages say `{* ../../docs_src/first_steps/tutorial001_py310.py *}` instead of
showing code. Like a recipe book that says "see page 112" for every recipe: the search found
the right page, but the recipe was missing. This step fetches page 112 and pastes it in.

**Files:** `src/docpilot/ingestion/includes.py`, `tests/test_includes.py`;
`scripts/01_download_docs.py` (also downloads the 18 code files, same pinned commit, into
`data/code/fastapi/`, gitignored); `scripts/02_ingest.py --includes`.

**Checked before building:** the code lives at the FastAPI repo root (`docs_src/...` -> HTTP
200; `docs/en/docs_src/...` -> 404).

**Rules:** a missing file is reported and its marker kept, never hidden; the code goes in
as a ```python block, so the cleaner and later chunkers treat it as code.

**Result (dry run, 2026-10-17):** includes resolved **29**, missing **0**; the "minimal app"
chunk now holds real code. Chunks 51 -> 57 (the code adds text). Fixes the cause of
failure-log Q1 (invented code) and q-007 (false refusal), to be measured.

**Run (hands-on):**
```powershell
python scripts/01_download_docs.py
python scripts/02_ingest.py --clean --includes --collection docpilot_clean_incl
python -m evals.run_retrieval_eval --collection docpilot_clean_incl --split dev --config-id C0+clean+incl
```
**Real results:** n/a (your run).

---

## 33. Step 2.5: metadata on every chunk (2026-10-17, not yet committed)

**Goal:** every chunk knows where it came from and what is inside it. Like a label on every
jar in a pantry: what it is, where it came from, when it was made.

| Field | Example | Used for |
|---|---|---|
| technology | `fastapi` | filters in Phase 3 ("only Docker docs") |
| domain | `docs` (learning / interview later, D-030) | per-domain scores (2.9) |
| doc_type, version | `tutorial`, commit `d623544...` | "which docs version said this?" |
| heading_path | `["Query Parameters", "Defaults"]` | better citations |
| has_code, has_table | `True`, `False` | per-type analysis |
| content_hash | sha256 of the text | spot duplicates, re-embed only changes |

**Files:** `ingestion/sources.py` (one place for source facts; the download script reads its
pinned commit from here), `ingestion/metadata.py`, `tests/test_metadata.py`.

**Rules:** `#` inside a code block is a comment, not a heading; a document with no register
entry stops ingestion (unknown licence, D-030). Metadata goes into the Qdrant **payload
only**; the embedded text is unchanged, so retrieval scores do not move.

**Real results:** 5 tests; full suite 83 passed (2026-10-17).

---

## 34. Step 2.4: the block parser (2026-10-17, not yet committed)

**Goal:** see the document as **pieces with a meaning** (heading, paragraph, code, table,
list), so the chunkers of 2.6 can keep them whole. Like cutting a cake along its layers
instead of with a ruler every 8 cm.

**Files:** `src/docpilot/ingestion/blocks.py`, `tests/test_blocks.py`.

| Rule | Why |
|---|---|
| Everything between two ``` fences is ONE code block | code must never be cut |
| `# comment` inside code is not a heading | Python comments start with `#` too |
| Table rows (`|`) and list items (`*`, `-`, `1.`) stay together | q-018's answer was a list cut in two |
| Each block remembers its heading path | "Request Body > Results", for citations and the hierarchical chunker |

**Plan fixes:** heading anchors `{ #x }` removed (one shared `parse_heading`, also used by
metadata); a `list` kind added (the plan treated lists as paragraphs); `#hashtag` without a
space is not a heading.

**Result on the real pages:** 0 lines lost; 63 code blocks = 63 fence pairs; 16 lists;
q-018's answer is one whole block. No tables exist in these pages yet (2.7, 2.8 bring them).

**Not used yet:** today's fixed chunker ignores blocks; 2.6's chunkers will build on them.


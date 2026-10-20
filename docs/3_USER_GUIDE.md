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


---

## 35. Did clean data help? And the first piece of step 2.6 (2026-10-17)

**The two data-quality runs** (same exam: 19 dev questions; same fixed 800/100 chunks;
only the text changed):

| Config | Recall@1 | Recall@5 | MRR |
|---|---|---|---|
| C0 (raw) | 0.526 | 0.842 | 0.667 |
| C0+clean | 0.526 | 0.947 | 0.665 |
| C0+clean+incl | 0.474 | 0.895 | 0.643 |

**In plain words:** cleaning pulled 2 more questions into the top 5. Pasting the real code
in pushed code answers to rank 1 but pushed some prose answers down, because the new code
chunks compete with the text. One question = 0.053, so these moves are 1 to 2 questions.
We keep both (D-039): the final system needs the code, and the smarter chunkers of 2.6 are
supposed to stop code and prose from getting mixed.

**Why tokens now (D-038):** the model reads **tokens** (word pieces), not characters, and
quietly ignores everything after 512 of them (510 for our text: 2 seats are taken by the
start and end markers). Like a bus with 512 seats: extra passengers are left behind and
nobody tells you. `chunkers/tokens.py` counts seats with the model's own tokenizer, and
`02_ingest.py` now prints the biggest chunk and how many are over.

**Small bug fixed:** a new result file made the next run look "+dirty". Result files are
outputs, not code, so they no longer count.

---

## 36. The ruler, now in tokens, and a label on every library (2026-10-19)

**Fixed chunker in tokens:** same ruler as C0, but it measures in **tokens** (what the model
reads) instead of characters. 400 tokens with 50 overlap gives 36 chunks on our 4 pages
(800 characters on the same clean + includes text gave 57). It still cuts through code and lists on purpose: it is the
**control row**. When the recursive chunker (C1) is tested at 400 tokens, we compare it with
this one at 400 tokens. Then the only difference is *where* we cut, not *how big*.

**Why it slices the original text:** the tokenizer lower-cases words and drops spaces. If we
glued tokens back together, code would lose its indentation. So we remember where each token
starts and ends in the page and cut the page itself at those places.

**A label on every library (D-040):** every collection now gets a small file saying how it
was built (strategy, size, overlap, cleaned, includes). Before, the eval copied the settings
from `config.py`, so a recursive-400 run would have been written down as "fixed 800": like a
lab sample with the wrong sticker. The eval now reads the label, and MLflow shows it too.

---

## 37. Step 2.6: six ways to cut a page (2026-10-19)

All chunkers cut the page at exact character positions, so a chunk is always a real piece
of the page (0 characters lost, checked on all 4 pages).

| Strategy | How it cuts (like ...) | On our 4 pages |
|---|---|---|
| fixed_tokens (control) | a ruler every 400 tokens | 36 chunks; 7 of 79 code/list blocks cut |
| C1 recursive | tear at chapters, then paragraphs, then sentences | 37 chunks; 2 of 79 cut |
| C2 semantic | cut where the topic jumps (sentence vectors) | 64 chunks; 0 cut; some tiny |
| C3 parent-child | find the line in the index, read the whole page | 131 children, 62 parents |
| C4 hierarchical | cut a cake along its layers; label each slice | 65 chunks; 0 of 79 cut |
| C5 contextual | C4 + an LLM "sticky note" on every chunk | needs about 65 LLM calls |
| Q&A pairs | never split a question from its answer | for interview files (2.8) |

**Two lessons from building them:**
1. *One change per row.* C4 with and without the heading prefix first made 66 vs 65
   chunks, so two things changed. Fixed: the size now ignores the prefix.
2. *Free tiers shape design.* Groq allows 8000 tokens a minute. Sending the whole page with
   every chunk would allow only 2 notes a minute, so C5 sends the chunk's section instead.

**The fixed_tokens-400 result** (Recall@5 0.684, down from 0.895) showed that size alone
matters: bigger chunks are blurrier. That is why every strategy is also tested at 200.

---

## 38. Which way of cutting won? (2026-10-19)

**Your guess:** recursive. **Result:** recursive tied for the best Recall@5 (0.895), but so
did three others, so Recall@5 could not choose. The tie-breakers were the rank metrics:

| Config | Recall@1 | Recall@5 | MRR | Tokens sent to the LLM (p50) |
|---|---|---|---|---|
| C0 (raw, 800 characters) | 0.526 | 0.842 | 0.667 | 1013 |
| C1-400 recursive | 0.526 | 0.895 | 0.679 | 1372 |
| C3-128 parent-child | 0.579 | 0.895 | 0.696 | 1211 |
| C4-400 hierarchical | **0.737** | 0.842 | **0.795** | 1011 |
| C4-200 hierarchical | 0.684 | 0.895 | 0.782 | **575** |
| C2-400 semantic | 0.316 | 0.789 | 0.537 | n/a |

**In plain words:** cutting along the page's own layout (hierarchical) puts the right chunk
**first** far more often: 14 of 19 questions at rank 1, against 10 for C0. C4-400 and C4-200
are a tie (1 question apart), so we pick the one that sends the LLM **43% fewer tokens**:
C4-200 (D-042). It is "provisional": the final pick happens in 2.9 on a bigger exam.

**How to check that a strategy fits low latency** (a time budget, like a household budget):
1. *Search time:* about 2 ms for every strategy, so it never decides.
2. *Tokens sent to the LLM:* the LLM was about 96% of C0's time, and it reads every token
   we send. Measured without any LLM call: C4-200 sends 575, C0 sends 1013.
3. *Free-tier limit:* Groq allows 8000 tokens a minute; fewer tokens per question means
   fewer "429 wait" pauses (C0 had 15).
4. *Proof:* run the real latency test (22 LLM calls) for C4-200 and C0 on the same day,
   and the abstention check, to confirm the smaller context did not hurt answers.

---

## 39. Step 2.7: DocPilot reads PDF and Word (2026-10-19)

**Why a special reader:** a PDF stores *where letters sit on a page*, not "this is a table".
Pull the text out naively and a results table becomes a row of loose numbers. Docling looks
at the page like a person (small layout and table models) and writes clean Markdown, so a
PDF goes through the same cleaner, chunkers and eval as a FastAPI page.

| File | Source | Result |
|---|---|---|
| `ragas/ragas_2309.15217v2.pdf` | RAGAS paper, CC BY 4.0 | 8 pages, 4 tables, 26 s warm |
| `interview/phase_1_notes.docx` | your own notes + your real C0 table | 1 table, exact |

**Lessons:**
1. *Read the defaults:* OCR was ON by default; we switched it off (digital files only).
2. *Packages can lie about their needs:* the table model needed OpenCV without saying so.
3. *Slow steps get a cache:* 26 s per paper is fine once; a re-ingest now takes 0.03 s.
4. *A new exam needs a new label:* 8 table questions were added, so the golden set is now
   v0.1 (40 items). Old v0 rows stay valid for the old exam only.

**Commands:** rebuild the old corpus with `--sources fastapi`; the full corpus without it.

---

## 40. The PDF is now the Chain-of-Thought paper (2026-10-20)

**Why the swap:** the RAGAS *paper* (a document on the shelf) was easy to confuse with the
RAGAS *library* (a grading tool we have not installed). So the PDF is now a paper on a
topic DocPilot does not use as a tool: **Chain-of-Thought prompting** (Google, 2022), the
idea of asking an LLM to "think step by step". It is a classic interview topic.

| Thing | Where it lives |
|---|---|
| The PDF | `data/docs/cot/cot_2201.11903v6.pdf` (not in git; `scripts/01_download_docs.py` re-downloads it and checks its fingerprint) |
| Docling's Markdown of it | `data/processed/converted/cot/cot_2201.11903v6.pdf.md` |
| Its register entry (licence, version) | `src/docpilot/ingestion/sources.py`, key `cot` |
| Its 4 exam questions | `evals/golden/dev.jsonl` (q-041, q-042, q-043), `test.jsonl` (q-044) |

**The 4 new questions** (each answer is one row of a table):
q-041 LaMDA 420M on GSM8K with CoT (0.4%: CoT hurts tiny models); q-042 did CoT help
GPT-3 on CSQA (no: 79.5 vs 73.5); q-043 PaLM 62B on GSM8K (9.6 vs 29.9); q-044 PaLM 540B
on StrategyQA (68.6 to 77.8, hidden test question).

---

## 41. Step 2.8: a bigger library and a bigger exam (2026-10-20)

**The library (corpus v1): 20 documents in 3 rooms (domains).**

| Room | Books | Licence |
|---|---|---|
| docs | FastAPI (4 pages), Pydantic (3), Docker (5) | MIT, MIT, Apache-2.0 |
| learning | Chain-of-Thought paper (PDF), Wikipedia: RAG, word embedding, IR evaluation | CC BY 4.0, CC BY-SA 4.0 |
| interview | your notes: phases 0, 2, 3 (Markdown) + phase 1 (Word) | your own work |

The **register** (`src/docpilot/ingestion/sources.py`) is the library's catalogue card for
each book: where it came from, which exact version, which licence, when we checked. A test
fails if a card is incomplete. `python scripts/01_download_docs.py` rebuilds the library.

**The exam (golden v1): 65 questions**, 46 practice (dev) and 19 final (test), at least 10
per room. Every question now says which room its answer is in (`domain`), so we can see if
a strategy is good for docs but bad for interview notes.

**Lesson from this step:** adding books can make an old "not in the library" question
answerable. q-003 ("which status code on validation failure?") was "not in the docs", but
your Word notes say "422". Now it is a normal question. Rule: after adding documents,
re-check every unanswerable question.

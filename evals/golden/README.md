# Golden dataset v1 (Phase 1 step 1c; extended in Phase 2 steps 2.7 and 2.8)

**v1 (2026-10-20, D-045):** 65 items, dev 46 + test 19, three domains: docs 41 (5
unanswerable), learning 12 (1), interview 12 (1). Every item has a `domain` (where the
answer lives; checked against `ingestion/sources.py`). New types `concept`, `interview`.
q-003 is answerable now (the Word notes say 422). Version is in `evals/golden/VERSION`.

**v0.2 (2026-10-20, D-044):** the RAGAS PDF was replaced by the Chain-of-Thought paper
(`cot/cot_2201.11903v6.pdf`). q-033..q-036 removed; q-041..q-044 added (table rows of
Tables 2 and 4). Still 40 items: dev 28 (3 unanswerable), test 12 (2).

**v0.1 (2026-10-19):** v0 + 8 table questions (q-033 to q-040): 4 on the RAGAS paper PDF
(`ragas/ragas_2309.15217v2.pdf`), 4 on the Word notes (`interview/phase_1_notes.docx`).
Snippets for PDF/DOCX are copied from the Docling Markdown (`data/processed/converted/`),
which is what the validator checks. Now 40 items: dev 28 (3 unanswerable), test 12 (2).
Rows measured on v0 (32 items, FastAPI only) are not comparable with v0.1 rows.

The answer key for DocPilot. Without it "better" is an opinion; with it, it is a number.
Decision: D-032 (design), D-010 (labels are document + verbatim snippet).

| File | Items | Unanswerable | Used when |
|---|---|---|---|
| `dev.jsonl` | 22 | 3 | every experiment (look, tune, repeat) |
| `test.jsonl` | 10 | 2 | **only at phase gates**, never for tuning |
| total | 32 | 5 (16%) | |

Corpus: the 4 FastAPI pages of D-029 (commit `d62354434b2e`). If the corpus changes, run
the validator: a snippet that moved or changed fails loudly.

## One item

```json
{"id": "q-001", "question": "How do I make a query parameter optional?", "type": "how-to",
 "should_answer": true, "reference_answer": "Give it a default value of None; ...",
 "evidence": [{"doc": "fastapi/query-params.md", "snippet": "you can declare optional query parameters, by setting their default to `None`"}],
 "difficulty": "easy", "split": "dev", "notes": "..."}
```
(Shown on several lines here; in the file each item is one line: that is what JSONL means.)

| Field | Meaning |
|---|---|
| `type` | one of the 8 types below |
| `should_answer` | `false` = the answer is in none of the pages; DocPilot must say `NOT_FOUND` |
| `reference_answer` | what a correct answer says (used by generation evals in Phase 3.9) |
| `evidence` | where the answer is: `doc` = path under `data/docs/`, `snippet` = text copied **exactly** from that file, one line, short |
| `difficulty` | easy / medium / hard, the writer's guess, checked against results later |
| `notes` | why the item exists, traps, links to failure-log rows |

**Why a snippet and not a chunk id (D-010)?** Chunk ids change with every chunking
strategy; the text of the page does not. The same answer key works for all six Phase 2
strategies. A snippet cut across two chunks is handled by an overlap rule in
`evals/matching.py` (step 1d).

## Types covered

| Type | Dev | Test | Example id |
|---|---|---|---|
| factual | 5 | 1 | q-011 |
| how-to | 3 | 2 | q-001 |
| exact-identifier | 3 | 1 | q-004 |
| paraphrase | 2 | 1 | q-005 |
| comparison | 2 | 1 | q-006 |
| multi-hop | 1 | 1 | q-010 |
| table-or-code | 3 | 1 | q-007 |
| not-in-docs | 3 | 2 | q-002 |

Not covered yet, on purpose (PROJECT_DOCUMENTATION section 2 lists them):
- **version-specific**: our 4 pages have one version only; comes with metadata (2.5, 3.8).
- **concept explanation, interview question**: need corpus groups B and C (2.8).
- **adversarial, risky**: tested by the red-team set in Phase 6, not by retrieval scores.

## Rules this set follows

1. The 10 questions from step 1b (`docs/failure_log_phase1.md`) are q-001 to q-010 and are
   all in **dev**: we have already looked at their answers, so they cannot be "unseen".
2. Test items are new questions nobody has run yet. Running test to choose settings would
   turn it into a second dev set; then the gate score is no longer honest.
3. Unanswerable items are **near-misses** where possible (q-003 status code, q-030 JWT,
   q-032 max length): the pages look related, so the search returns convincing chunks.
4. Item q-007 (minimal app code) has evidence that the search can find while the answer
   still fails (the code is an include marker). Retrieval and generation scores will
   disagree on it, and that is the lesson. After step 2.3, add a code-line snippet.

## Check after every edit

```powershell
python evals/validate_golden.py
```
It checks: every line is JSON; all fields exist with allowed values; ids are unique across
both files; `should_answer` and `evidence` agree; each item sits in the file of its split;
**every snippet appears character for character in its document**. Tests:
`tests/test_validate_golden.py`.

## Who wrote it

2026-10-12: drafted by the mentor at the learner's request (time), every snippet copied
from the downloaded pages and checked by the validator. **Learner review pending:** read
each item, and change any question you would not ask yourself. You must be able to
explain every item at the Phase 1 gate.

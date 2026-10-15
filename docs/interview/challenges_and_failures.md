# Challenges and Failures: "Where did you get stuck, and how did you fix it?"

Interviewers ask this in almost every AI Engineer interview. They want to hear that you
**debug with evidence**, not that nothing went wrong.

**Rules for this file**
- Only **big** problems: ones that would have produced wrong results, wrong numbers, or a
  broken system. Small typos and lint errors do not belong here.
- Every entry is real and happened in this repo. Numbers come from real runs (`n/a` if
  unknown). Never add a story that did not happen.
- Practise each story **out loud** in your own words (2 minutes max), then write your
  version in `docs/interview_notes.md`.
- Add a new entry when a problem meets the bar above. Newest at the bottom.

**Story pattern: S-P-I-F-L** (Situation, Problem, Investigation, Fix, Lesson)

---

## 1. The "fresh" vector index that was not fresh (Phase 1, step 1a.5, 2026-10-12)

- **Situation:** every ingest must start from an empty Qdrant collection, so each
  chunking experiment in Phase 2 is measured on its own chunks only.
- **Problem:** my test `test_fresh_collection_is_empty` failed with `assert 3 == 0`.
  After deleting and recreating the collection, the 3 old points were still there.
- **Investigation:** with fake 4-number vectors I checked step by step:
  `delete_collection` returned `True` and the collection reported it no longer existed,
  yet `create_collection` loaded the old points back. In-memory mode did not do this; the
  on-disk `storage.sqlite` file stayed after the delete. Likely Windows file locking (not
  confirmed).
- **Fix:** after creating the collection, delete all points with an empty filter, then
  **fail loudly** if any remain (qdrant-client 1.19.1, local mode; decision D-027).
- **Why it was big:** every Phase 2 re-index would silently mix chunks from the previous
  strategy. All comparison numbers (C1 to C5) would be wrong, with no error anywhere.
- **Lesson:** test the infrastructure layer, not only your own logic. A five-line test
  caught a storage bug that would have corrupted every experiment.

## 2. Silent quality bugs in the embedding layer (Phase 1, step 1a.4, 2026-10-12)

- **Situation:** BGE-small needs an instruction prefix on **questions only**, and my labs
  used a pinned model revision.
- **Problem (two silent traps):** (a) the plan loaded the model without a revision, so the
  app could use different model files from the labs if Hugging Face updated them;
  (b) sentence-transformers 6.1.0 has an `encode_query()` helper that looks correct, but
  this model's stored query prompt is an **empty string**, so it would silently skip the
  prefix.
- **Investigation:** inspected the installed library and the loaded model
  (`model.prompts` returned `{'query': '', 'document': ''}`) instead of trusting the
  method name.
- **Fix:** pin `revision=` in one place (`config.py`) and add the prefix explicitly in
  `embed_query`.
- **Why it was big:** neither bug raises an error. Retrieval would just get a bit worse and
  the baseline number would be quietly wrong or not reproducible.
- **Lesson:** a convenience method is only correct if its configuration is. Silent bugs are
  the dangerous ones in ML systems, because nothing crashes.

## 3. Making eval numbers reproducible across machines (Phase 1, steps 1a.2 to 1a.8)

- **Situation:** my eval numbers will be compared across runs, on my Windows laptop and on
  Linux CI. The same input must give the same chunks in the same order everywhere.
- **Problem:** found three ways the same docs could give different chunks:
  (a) `sorted()` on paths ignores case on Windows but not on Linux, so document order could
  differ; (b) `write_text` on Windows turns `\n` into `\r\n`, adding characters, so
  800-character chunks would be cut at different places; (c) downloading docs from
  `master` means the corpus changes whenever the upstream project edits a page.
- **Fix:** sort by the relative-path string; save downloads with `write_bytes`; pin the
  corpus to one Git commit (D-029), just as packages and the model are pinned.
- **Why it was big:** without this, a number could change between my laptop and CI for
  reasons unrelated to my code, and I could not trust any comparison.
- **Lesson:** reproducibility is designed in, not hoped for. Pin everything that feeds a
  metric: code, packages, model, data.

## 4. The LLM provider did not match its own docs (Phase 1, step 1a.6, 2026-10-12)

- **Situation:** the plan expected a Llama model on Groq's free plan.
- **Problem:** Groq's docs page listed `llama-3.3-70b-versatile`, but calling it with my key
  gave `NotFoundError: 404 ... model_not_found`. Also, the model I chose (`gpt-oss-120b`)
  is a reasoning model: its thinking can use the default 1024-token budget and return an
  **empty** answer, which my code turned into `""` without any error.
- **Investigation:** asked the API itself (`GET /models` with my key) instead of trusting
  the docs page: the account offered gpt-oss and qwen, no Llama. Read the provider's
  reasoning docs for where the answer and the thinking are returned.
- **Fix:** model chosen from the account's real list and recorded with the date (D-028);
  `chat()` now raises with `finish_reason` when the answer is empty, instead of returning
  `""`, which evals would have scored as a normal wrong answer.
- **Lesson:** free-tier providers change fast. Verify against the live API, record the date,
  keep the provider a setting (one line in `.env`), and make empty outputs fail loudly.

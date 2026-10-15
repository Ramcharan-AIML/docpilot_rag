# DocPilot Progress (part 2)

Continues the session log of [progress.md](progress.md) ("Right now" and the phase
checklist stay there). Newest session on top.

---

## Session log

### 2026-10-15, session 14: Phase 2 starts; step 2.0 MLflow; PDF/Word; resume entry

- Learner: "yes, yes" (follow the ablation table: C1-C5 in Phase 2; build 2.0). Asked for
  PDF and Word support ("more important") and a resume title/description/tech list.
- Branch `phase-2-chunking` from `main` (after the `phase-1` merge).
- 2.0: PyPI 2026-10-15: mlflow 3.17.1, mlflow-skinny 3.17.1 (skinny has no UI/SQL ->
  full mlflow, dev only). Installed: 60 new packages, protobuf 7.36.2 -> 6.33.6, `pip
  check` clean. Files: `config.py` (`CHUNK_STRATEGY`, `MLFLOW_TRACKING_URI`,
  `MLFLOW_ARTIFACT_DIR`), `.gitignore` (mlflow.db, mlartifacts/, mlruns/),
  `evals/common.py` (`golden_version`, `chunk_strategy` in settings),
  `evals/tracking.py`, runners log automatically (+ `--ablation`),
  `evals/relog_results_to_mlflow.py` (moved from the plan's `scripts/`: imports `evals`),
  `tests/test_tracking.py` (4). Full suite 66 passed. D-036.
- Smoke re-log into a throwaway DB: 4 C0 files logged, second run skipped all,
  recall_at_5 / mrr / total_p50_ms / accuracy equal to the JSON, JSON attached; DB and
  artifacts deleted (learner does the real run).
- PDF/Word: Docling lists PDF and DOCX (docs page 2026-10-15; docling 2.139.0). Step 2.7
  widened to PDF + Word + HTML; corpus files only, uploads stay 8.6 (D-037).
- Resume: `docs/interview/resume_entry.md` (titles, version A = true today with real
  numbers, version B = target with n/a placeholders, skills line, checklist).
- `decisions.md` is at 495 lines: the next decision entries go to `2_decisions.md`.

### 2026-10-15, session 13: Phase 0 and Phase 1 gates closed

- Learner (no time) asked the mentor to write the remaining gate texts and complete
  Phase 1, then move to Phase 2 "with my word". Mentor flagged that the gate asks for the
  learner's own words; texts are written and **clearly marked as mentor drafts**.
- Written: failure-log three lines (final, linked to the 1d numbers); `interview_notes.md`
  Lab 2 two sentences + Phase 0 Q1-Q4 + Phase 1 Q1-Q3 (honest-status note at the top).
- Phase 0 gate: Lab 2 sentences and notes done (mentor drafts); tag `phase-0` on
  `0a1e689` (last Phase 0 commit, already on `main`).
- Phase 1 gate checklist: pytest green (62, local + GitHub); failure log 10 rows + 3
  lines; golden v0 passes validator; C0 dev + test run once; abstention 0.909; L0
  recorded; versions pinned (D-026 to D-035); notes (mentor drafts); CI green; branch
  protection deferred (private repo, D-035); PR #1 merged; tag `phase-1`.
- Phase 2 not started yet: first step 2.0 is teaching MLflow from zero.

### 2026-10-15, session 12b: Phase 1 gate, test split run once (learner)

- Prediction: not given (third run in a row without one).
- Real output, `python -m evals.run_retrieval_eval --split test --config-id C0`, commit
  `ccd45ec` clean, n=8 answerable test items: Recall@1 0.375, Recall@3 0.875,
  **Recall@5 1.000**, strict Recall@5 0.938, **MRR 0.635**, **nDCG@5 0.687**; search
  p50 1.2 ms, p95 1.8 ms. File `evals/results/2026-10-15_C0_test_retrieval.json`.
- Reading: consistent with dev (finds well, ranks first rarely: 3 of 8 at rank 1).
  Recall@5 1.000 vs dev 0.842 is within noise (n=8: one question = 12.5 points); no
  sign of overfitting (nothing was tuned on dev either). Test must not be used for tuning.
- Learner asked "is next Phase 2?": not yet. Phase 1 gate still needs the 3 summary lines
  and Phase 1 interview notes in the learner's own words, merge of PR #1, tag `phase-1`.
  Phase 0 gate is also still open (Lab 2 sentences, Phase 0 notes, tag `phase-0`), and
  CLAUDE.md forbids starting phase N+1 before phase N's gate passes.

### 2026-10-15, session 12: first CI run on GitHub (learner)

- Learner committed 1d abstention + guide (`72697d3`), 1e (`9e18b96`), 1f (`656cb64`),
  pushed, and opened **draft PR #1** `phase-1-baseline -> main` with the filled template
  (https://github.com/Ramcharan-AIML/docpilot_rag/pull/1). Prediction: not given.
- Real result: **ci / test green**, run `38682492687`, 1 min 36 s, ubuntu-latest:
  CPU-only `torch-2.14.1+cpu` (196.3 MB wheel), ruff clean (38 files), **62 passed in
  12.39 s**, length check OK. A second check, **GitGuardian Security Checks** (an app on
  the learner's GitHub account, not part of our workflow), reported no secrets.
- Draft PR stays open until the Phase 1 gate; merge only when green (no branch
  protection while private, D-035).

### 2026-10-14, session 11: steps 1e (mini API) and 1f (CI files); evals guide

- Learner asked: build 1e and 1f, and write one complete evals guide with interview Qs.
- 1e: PyPI checked (fastapi 0.143.1, uvicorn 0.54.0, httpx 0.28.1), installed, `pip
  check` clean; D-034. `src/docpilot/api.py`, `tests/test_api.py` (4 tests: valid 200,
  empty 422, 3000 chars 422, wrong field 422). Uvicorn booted for a check: `GET /docs`
  200, `/openapi.json` lists `/ask`. A live `/ask` call was not made (learner's run).
- 1f: `.github/workflows/ci.yml`, `.github/pull_request_template.md`,
  `scripts/check_file_lengths.py`; lock file regenerated (+fastapi, starlette,
  uvicorn, opentelemetry-api). Fixes: ruff `extend-exclude = ["docs"]`; compact result
  JSON (744 -> 117 lines, data identical); Pyrefly `search-path`. D-035.
- CI simulated locally with `GROQ_API_KEY`, `LLM_MODEL` blank: 62 passed; ruff check and
  format clean on the whole repo; length check OK.
- GitHub: repo is PRIVATE; branch protection API answers 403 "Upgrade to GitHub Pro or
  make this repository public". History scan: 21 commits, no secrets or data files;
  author email would be public. **Learner's decision:** repo stays private until the
  whole project is finished (email visibility is fine). Branch protection and the
  "direct push rejected" gate item are deferred to project end (D-035, memory saved).
  CI still runs on PRs; first real CI run pending the learner's push and PR.
- Evals guide: `docs/teaching/evals_guide.md` + `2_evals_guide.md` (concepts with this
  project's real numbers; direct and scenario interview questions with answers).

### 2026-10-14, session 10c: abstention check (learner run)

- Learner predictions: not given. Run: `python -m evals.run_abstention_check --split dev
  --config-id C0`, commit `b061d62` clean, Groq `openai/gpt-oss-120b`, n=22.
- Real output: **accuracy 0.909** (20/22); answered although it should refuse **0/3**;
  refused although it should answer **2/19**: q-007 (minimal app code: only `{* ... *}`
  markers indexed) and q-017 (GET "payload": right chunk at rank 6, outside the 4 given to
  the LLM). Both false refusals trace back to ingestion and retrieval, not to the LLM.
- 429 waits again on most questions (free tier). Step 1d complete on dev.

### 2026-10-14, session 10b: latency baseline L0 (learner run)

- Learner's paper check of q-001 `[0, 1, 0, ...]`: Recall@1 0, @3 1.0, @5 1.0, RR 0.5:
  all correct. Latency predictions: not given.
- Real output, `python -m evals.run_latency --split dev --config-id C0`, commit `8295859`
  clean, laptop CPU (Windows 11), Groq `openai/gpt-oss-120b`, 1 warm-up, sleep 2 s,
  n=22: embed_query p50 15.8 / p95 85.4 / max 102.9 ms; search 1.0 / 1.9 / 2.4 ms;
  llm 1060.4 / 1748.8 / 1858.6 ms; **total 1107.2 / 1763.7 / 1945.5 ms**;
  wall incl. 429 waits 5933.9 / 8208.5 / 8238.2 ms.
- **15 rate-limit (429) retries** from question 9 on (q-012 twice); server asked to wait
  1 to 7 s. Which Groq limit (requests or tokens per minute) was hit: n/a, headers not
  logged. The `total` column excludes the waits; `wall_with_retries` includes them.
- Lesson: the LLM is about 96% of total time (1060 of 1107 ms at p50); embedding warm is
  about 130x faster than the 1b cold runs (about 2000 ms incl. model load).

### 2026-10-14, session 10: C0 retrieval eval, run by the learner (hands-on)

- Learner asked for a hands-on walkthrough (terminal, venv, reading the table and the
  JSON). Mentor guide: activate venv, `git restore` a stray editor comment (Pyrefly
  `ignore` line in `evals/common.py`) so the run is not `+dirty`, predict, run, read.
- Learner prediction (before the run): "about 3 of 19 will have the right chunk in the
  top 5, because it has the high recall@5" (circular reason). Hand check of q-005: not
  done (learner answered "all metrics are 5 only"; explained in chat).
- Real output, `python -m evals.run_retrieval_eval --split dev --config-id C0`, commit
  `06891f1` clean, laptop CPU: n=19; Recall@1 0.526, Recall@3 0.842, **Recall@5 0.842**,
  strict Recall@5 0.781, **MRR 0.667**, **nDCG@5 0.670**; search p50 1.3 ms, p95 2.2 ms
  (warm, n=19). File `evals/results/2026-10-14_C0_dev_retrieval.json`.
- Misses at @5 (3 of 19): q-017 paraphrase (GET "payload" vs doc "body", rank 6), q-018
  table-or-code (bullet list, 1 of 2 snippets at rank 6), q-023 how-to (path-param Enum
  "fixed set of allowed values" vs doc "predefined values"; not in top 10, the
  query-params Enum tip wins). Per-type rows have n = 1 to 5: read as examples, not scores.
- `evals/ABLATION.md` C0 retrieval columns filled. Next: L0 latency, abstention (hands-on).

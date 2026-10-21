# DocPilot Progress (part 2)

Continues the session log of [progress.md](progress.md) ("Right now" and the phase
checklist stay there). Newest session on top.

---

## Session log

### 2026-10-21, session 33: step 3.2 BM25 (lab by hand, then FastEmbed) (D-052)

- Learner committed 3.1b (`95342ef`). Explained SeaweedFS, boto3, BM25 (learner asked).
- Lab 3 (learner ran it): IDF "the" 0.288 vs rare words 1.386; "max_length" -> sentence 1
  only (1.551, others 0); "query parameter" -> short sentence 1 beat long sentence 5 (length
  penalty); "validate" did not match "validated" (no stemming); tf 10 -> 1.966 vs tf 1 ->
  1.005 (ceiling 2.2). Learner did not predict (new topic); explanation given after.
- FastEmbed 0.8.1 BM25 + named vectors dense/sparse + IDF modifier; avg_len 78.6 measured.
  +5 tests (170). Try run: dense unchanged; sparse R@5 0.805, MRR 0.658; best of both 36/41.

### 2026-10-21, session 32: step 3.1b object storage + MLflow server (D-051)

- Learner committed 3.1 (`d064d6f`). Built SeaweedFS 4.48 + MLflow 3.17.1 server (own
  Dockerfile adds boto3) in Compose; object_store.py, 04_sync_docs.py, ingest --from-s3,
  snapshots.py + snapshot_index.py; boto3 1.43.116, moto 5.2.4 (+4 moto tests, 165 total).
- Done checks: 39 files byte-identical after round trip; index from the S3 copy and from
  a restored snapshot both give R@1 0.634 / R@5 0.805 / MRR 0.701; MLflow server holds 32
  re-logged runs, artifacts in SeaweedFS, ABLATION.md regenerated identical.
- Found: bind mounts in OneDrive made a 453-point collection 593 MB and a snapshot take
  91 s (621 MB); named volumes: 2 MB in 0.3 s. Also fixed a too-long comment from 3.1.

### 2026-10-21, session 31: Phase 2 merged; step 3.1 Qdrant in Docker (D-050)

- Phase 2 gate closed: PR #3 merged (test + eval-gate green), tag `phase-2`.
- 3.1: docker-compose.yml (qdrant v1.19.1, amd64+arm64 checked), `QDRANT_URL` server mode
  in `get_client()` (default empty = local, for tests/CI; plan bug fixed), +1 test (161).
- FT-200 re-ingested into Docker (453 points): scores identical to local on all 41 dev
  questions. Learner predicted "recall same, latency changes": correct.
- Found: `localhost` costs ~2 s per request on Windows (IPv6 first); `127.0.0.1` -> search
  p50 7.6 / p95 17.7 ms (local mode 3.7 / 4.0).

### 2026-10-20, session 30: red-PR demo done, Phase 2 gate prep

- Learner committed 2.10 (`f60ab50`) and ran the demo: PR #2 (units bug) -> `eval-gate`
  fail (1m51s), `test` pass; PR closed, branch deleted (never merged).
- Learner chose to skip C5 contextual (D-049). Phase 2 interview answers drafted by the
  mentor in `interview_notes.md` (learner request; to be rewritten in own words).
- Next: PR phase-2-chunking -> main, merge on green, tag `phase-2`.

### 2026-10-20, session 29: step 2.10 CI eval gate (D-048)

- Learner committed 2.9 (`cfd01a5`). Built: fixture corpus (7 own Lumen pages,
  register `ci_fixture`), `evals/golden/ci.jsonl` (18 + 1), `--golden/--output` in the
  retrieval eval, `evals/check_gate.py`, `scripts/ci_gate.py`, job `eval-gate` in ci.yml,
  env path overrides in config.py, ruff excludes tests/fixtures, primer_ci_eval_gate.md.
- Baseline R@5 1.000, MRR 0.870 (14 chunks); tolerance 0.06 / 0.05.
- Tested the test: units bug MRR 0.495, size 50 0.494, size 30 0.480 -> fail; query
  prefix removed -> unchanged (not caught). Real dev without prefix: R@1 .585 vs .634,
  MRR .681 vs .701, R@5 same. Plan's demo break changed to the units bug.
- Tests 160 passed (+5); ruff clean; lengths OK. Learner: commit, then the red-PR demo.

### 2026-10-20, session 28: clean matrix, test split, FT-200 chosen (D-047)

- Learner committed fixes + tooling (`f4a3a49`) and chose FT-200 by the tie-break rule.
- Clean matrix re-run (15.6 min): every number identical to the dirty run.
- Test split once (n=17): FT-200 R@1 .471 / R@5 .882 / MRR .620; C0 .353 / .941 / .608.
  FT-200 does not beat C0 on recall; ranking gain only (dev+test R@1 34 vs 28 of 58).
- App switched: `config.COLLECTION_NAME = docpilot_v1_ft200`; `02_ingest.py --collection`
  now required. Phase 3 plan gets a chunking re-check item (top 3 after the reranker).
- Learner predictions: not given. Next: commit, then step 2.10 (CI eval gate).

### 2026-10-20, session 27: fixes A/B/C + first full chunking matrix (golden v1, dev)

- Fix A: includes resolved only when the source has a code folder (missing 1 -> 0).
  Fix B: cleaner shrinks table rows (dash runs -> ---, padding spaces). Fix C: a
  "Table N:" caption paragraph is merged into the table block below it. +4 tests (155).
- Matrix run on uncommitted fixes (`3778c0f+dirty`, 17.8 min, 11 configs); re-run after the
  learner commits. C0-v1 unchanged (0.780): the raw path is deterministic.
- R@5 (questions of 41): C3-128 .854 (35), C1-400 .829 (34), QA-400 .829 (34), C4-400 .805
  (33, best R@1 .659 / MRR .729), FT-200 .805 (33), C0 .780 (32), C4-200 .780 (32,
  was .756 before fixes; table-or-code .500 -> .625), FT-400 .780, C4-400-noprefix .756,
  C1-200 .732, C2-400 .732 (worst MRR .574).
- Top five are within 2 questions: a tie by our rule. Winner not chosen yet (learner).

### 2026-10-20, session 26: step 2.9 tooling (matrix + generated ablation tables)

- `scripts/run_chunking_matrix.py` (11 configs on golden v1 dev, C5 only with --with-llm),
  `evals/make_ablation.py` (main / per-type / per-domain tables between markers in
  ABLATION.md, numbers from the result JSONs of MLflow runs tagged ablation=true), D-046.
- `02_ingest.py` records `ingest_seconds`; MLflow de-dup now keys on file + commit.
- Plan bug fixed openly: `python evals/run_retrieval_eval.py` -> `python -m evals...`.
- Generator checked on the two real v1 runs: numbers equal the JSON files.
- Tests 151 passed (+8); ruff clean; file lengths OK. Matrix not run yet (needs a clean
  commit; fixes A/B/C would change the rows, so the learner decides the order).

### 2026-10-20, session 25: golden v1 baselines + "big picture" teaching note

- Learner committed 2.8 (`474161b`) and ran both v1 baselines (dev, n=41, no LLM):
  C0-v1 R@1 0.537, R@5 0.780, MRR 0.650 (441 chunks); C4-200-v1 R@1 0.585, R@5 0.756,
  MRR 0.669 (733 chunks). Search p50 2.2 / 3.1 ms. Tie within noise (1 question = 0.024).
  Rows + per-question reading in `evals/ABLATION.md` (v1 section).
- C4-200 losses q-045/q-047/q-049 = right document, wrong small piece; 4 of 7 shared misses
  are table-or-code (fixes B/C). CoT PDF does not crowd other domains (3 / 0 of 165 slots).
- Learner was confused about how to read the outputs and the project flow: wrote
  `docs/teaching/big_picture_and_reading_runs.md` (pipeline order, phases, golden set,
  ablation, every output line, latency, 6 end-of-run questions, decision rule).
- Prediction: not given. Next: fixes A/B/C, then 2.9 matrix (with a clean+includes fixed
  control row).

### 2026-10-20, session 24: step 2.8 corpus register + golden v1

- Learner committed the CoT swap (`178bd5f`) and asked for 2.8.
- Register grown in place (sources.py: topic, url, licence_url, checked) + test_sources.py.
  Licences checked today: Pydantic MIT, Docker docs Apache-2.0, Wikipedia CC BY-SA 4.0.
- Corpus v1 = 20 documents: FastAPI 4, Pydantic 3, Docker 5, CoT PDF, Wikipedia 3,
  interview notes 3 Markdown + 1 Word. `01_download_docs.py` rebuilds all (pinned commits,
  sha256, Wikipedia revision ids). Problems met: Python's Windows certificate store
  rejected Wikipedia (fixed with certifi); Wikipedia formulas = ~60 lines of symbols
  (only LaTeX kept); Docker front matter + Hugo shortcodes (cleaner rules, tests).
- Unanswerable re-check found q-003 answerable since 2.7 (Word notes say 422): corrected.
- Golden v1: 65 items (dev 46, test 19); docs 41, learning 12, interview 12; `domain` on
  every item, types concept/interview; VERSION file; validator checks domain vs register
  and >= 10 per domain. Retrieval eval prints a per-domain table.
- Dry run C4-200 on corpus v1: 733 chunks (CoT 364), largest 491 tokens, 0 over 510.
- Tests 143 passed (+11); ruff clean; validator OK. Fixes A/B/C still pending.

### 2026-10-20, session 23: PDF swapped to the Chain-of-Thought paper

- Learner ran ingest for fixed800 + C4-200 on the full corpus and the C4-200 eval (v0.1,
  `a727324`): n=25, R@1 0.600, R@5 0.800, MRR 0.688. Old 19 questions unchanged except
  q-018 (9 -> 10); new: q-037, q-039 rank 1, q-035 rank 4, q-038 rank 9, q-033/q-034
  missed (Table 1 chunk had no caption, headers abbreviated).
- Found 3 problems: (A) the notes quote an include marker, resolver reports "missing 1";
  (B) Docling pads table separator rows with up to 1150 dashes = 1150 tokens; fixed 800
  made 3 chunks of pure dashes (over 510); (C) a table chunk without its caption ranks low.
  Not fixed yet (waiting for the learner's word).
- Learner was confused by RAGAS paper vs RAGAS library and asked for another PDF that is
  not about this project's tools. Explained: RAGAS library not installed; generation
  evals not started (Phase 3.9).
- Swapped to Chain-of-Thought (2201.11903v6, CC BY 4.0, checked today; LoRA, Attention,
  DPR are non-exclusive). Docling: 43 pages, 8 tables, 182.4 s. Golden v0.2: q-033..q-036
  removed, q-041..q-044 added (unique table rows). RAGAS file and cache deleted; sources,
  download script (sha256), test, docs updated (D-044). Validator OK; 132 tests pass.

### 2026-10-19, session 22: step 2.7 Docling (PDF + DOCX)

- Learner committed `1de3d22` and ran C4-200 latency: p50 978 ms, p95 1230 ms, 9 retries
  (C0 on 2026-10-14: 1107 / 1764 ms, 15 retries; different days, C0-recheck not run).
- Learner chose: PDF = RAGAS paper (CC BY 4.0), DOCX = own notes. Licences checked on
  arXiv today: RAGAS CC BY 4.0, BEIR CC BY-SA 4.0, MTEB and Lost-in-the-Middle non-exclusive.
- Installed docling-slim 2.140.0 with 4 extras (24 packages, +89 MB; full docling = 54).
  First conversion crashed: table model needs cv2, undeclared -> pinned
  opencv-python-headless 5.0.0.93. typer 0.27.2 -> 0.26.8. CI installs torchvision from
  the CPU index. Lock file regenerated.
- RAGAS PDF: 8 pages, 4 tables, 36.4 s cold / 26.1 s warm; Table 1 exact; flaws recorded
  (heading spaces, hyphens, flat headings, a footnote in a prompt box). Notes DOCX
  (scripts/make_notes_docx.py, 15 Q&A + real C0 table): table exact, 8.0 s. Cache re-read
  0.03 s.
- Built `ingestion/document_loader.py` (cached by sha256 + Docling version), loader reads
  .pdf/.docx, validator checks snippets in the converted Markdown, sources `ragas` and
  `interview`, pinned RAGAS download with sha256, `02_ingest.py --sources`.
- Golden v0.1: +8 table questions q-033..q-040 (6 dev, 2 test); validator OK (40 items).
- Dry run C4-200: DOCX table whole; RAGAS Table 1 whole; appendix tables (704-1463
  tokens) split by rows, 0 chunks over 510. Tests 132 passed (+6); ruff clean.
- To run (learner, after commit): v0.1 rows for fixed 800 and C4-200 on the full corpus
  (commands in USER_GUIDE section 39 and the chat).

### 2026-10-19, session 21: chunking rows run; provisional leader C4-200

- Learner predicted "recursive has the best recall"; asked to skip C5 (65 LLM calls) and
  let the mentor run the rest; asked how to check that the winner fits low latency.
- Mentor ran 8 rows on clean commit `509d687` (dev, golden v0, n=19), all in ABLATION.md:
  R@1 / R@5 / MRR: fixed_tokens-200 0.579/0.789/0.684; C1-400 0.526/0.895/0.679; C1-200
  0.579/0.789/0.657; C2-400 0.316/0.789/0.537; C3-128 0.579/0.895/0.696; C4-400
  0.737/0.842/0.795; C4-200 0.684/0.895/0.782; C4-400-noprefix 0.684/0.842/0.744.
- Prediction: recursive tied for best Recall@5 (0.895, with C3-128, C4-200,
  C0+clean+incl) but is mid on Recall@1/MRR. Recall@5 alone cannot pick a winner here.
- Latency side measured without the LLM: search about 2 ms everywhere; LLM context p50
  (top 4): C0 1013, C1-400 1372, C3-128 1211, C4-400 1011, C4-200 575 tokens.
- Decision D-042: provisional leader C4-200 (ties C4-400 on quality, 43% less context).
  Final in 2.9 on golden v1 + test split. App still on C0.
- Flips read: q-023 missed by every block-based config (answer in its own sub-heading
  chunk); q-018 list whole now but outranked by code chunks (Phase 3 problem).
- `rag.ask()`, `ask_with_retries`, `run_latency.py`, `run_abstention_check.py` take
  `--collection` (before: C0 only). +1 test (126 passed); ruff clean.
- Optional next (22 LLM calls each, commit first):
  `python -m evals.run_latency --collection docpilot_hier200 --config-id C4-200`,
  same with `docpilot_naive --config-id C0-recheck` (same day = fair), and
  `python -m evals.run_abstention_check --collection docpilot_hier200 --config-id C4-200`.

### 2026-10-19, session 20: step 2.6 complete (all chunkers + parent scoring)

- Learner ran fixed_tokens-400 (`524f200`, manifest recorded correctly): R@1 0.474, R@5
  0.684, MRR 0.626, nDCG@5 0.607 (n=19). 13 questions changed rank vs C0+clean+incl;
  5 fell out of the top 5. Bigger chunks = blurrier vectors (ABLATION.md).
  Asked: which strategy is in use (the app still uses C0, `docpilot_naive`) and which is
  best (unknown until the rows are run). Asked mentor to finish all of 2.6 (learner: no time).
- Built (D-041): Block start/end; `Chunk.prefix`, `Chunk.parent_id`; `recursive.py` (C1),
  `semantic.py` (C2), `parent_child.py` (C3), `hierarchical.py` (C4, + noprefix variant),
  `contextual.py` (C5, ContextWriter: cache, 429 retries, cost stats), `qa_pairs.py`;
  `02_ingest.py` gained all strategies + `--base`; eval scores parent text automatically
  (plan 2.6.3, via the manifest instead of a flag).
- Verified: Groq headers 8000 tokens/min, 1000 requests/day (gpt-oss-120b and -20b).
- Dry run on the 4 pages (clean + incl): 0 characters lost and 0 bad slices for every
  strategy; code/list blocks split: fixed_tokens 7/79, recursive 2/79, hierarchical 0/79,
  semantic 0/79; hierarchical 65 chunks (median 174 tokens); semantic percentile 25 gave
  119 tiny chunks, set to 10 (64 chunks, median 174); parent-child 131 children, 62 parents
  (median 164, max 616). Q&A pairs on phase_1_interview.md: 15 pairs -> 15 chunks.
- Design fixes during the build: hierarchical size now counts text only (with/without
  prefix gave 66 vs 65 chunks = two changes in one row); semantic percentile now the same
  nearest-rank rule as evals/metrics.py; tokenizer fact: words over 100 chars = one [UNK].
- Smoke run (throwaway collection, deleted): parent-child ingest -> manifest + parents
  file -> 30 children lifted to 10 distinct parents. Tests 125 passed (+23); ruff clean.
- Rows to run (learner; commit first): fixed_tokens-200, C1-400, C1-200, C2-400,
  C3-128, C4-400, C4-200, C4-400-noprefix, C5 (contextual, about 65 LLM calls).

### 2026-10-19, session 19: fixed chunker in tokens; collection manifests

- Learner pasted the ingest summary only (no `chunk tokens:` line, no prediction); mentor
  measured: clean+incl fixed 800/100 chunks are 65 to 323 tokens (median 248), 0 over 510.
  Learner (no time): "go forward". Also asked whether we use LangChain/LangGraph: LangGraph
  from Phase 4 (plain loop first), LangChain only if a step needs it (plan 4).
- Built `fixed_token_chunks` (fixed.py; slices the original text between token offsets,
  refuses sizes over 510) and `token_offsets` (tokens.py); `config.CHUNK_TOKENS` 400,
  `CHUNK_OVERLAP_TOKENS` 50. `02_ingest.py` gained `--strategy`, `--size`, `--overlap`.
- Plan bug fixed (D-040): evals took chunk settings from config.py, so every new strategy
  would have been recorded as fixed 800/100. New `ingestion/manifest.py`; ingest writes
  `data/processed/collections/<name>.json`; `base_record` reads it (`settings_source`).
- Real pages (clean + incl): 200/25 -> 68 chunks, 400/50 -> 36 chunks; re-counted, no
  chunk over its size; 0 non-space characters lost. Tests: 102 passed (+8); ruff clean.

### 2026-10-17, session 18: data-quality rows recorded; 2.6 started (token counter)

- Learner committed 2.3-2.5 (`d8a3608`) and ran C0+clean and C0+clean+incl (no
  prediction given). Asked for clarity on cleaner, ingest, retrieval eval and the table;
  quiz answer for `[0,0,1,0,0]`: Recall@1 0 and Recall@5 1.0 right, MRR said 0, correct is
  1/3 (MRR is 0 only when nothing relevant is in the top 10).
- Results (dev, n=19, fixed 800/100): C0+clean R@1 0.526, R@5 0.947, MRR 0.665, nDCG@5
  0.703; C0+clean+incl R@1 0.474, R@5 0.895, MRR 0.643, nDCG@5 0.656. Flips and reading in
  `evals/ABLATION.md`. Decision D-039: chunkers run on clean + includes text.
- Bug fixed: `evals/common.git_commit` counted new result files, so the second
  back-to-back run said `+dirty`. Now `evals/results` is excluded.
- 512-token limit verified on the pinned model (D-038, new file `docs/2_decisions.md`
  because decisions.md is full). 3.07-3.46 chars/token on the 4 pages: C0 chunks are about
  250 tokens, no truncation so far.
- Built `ingestion/chunkers/tokens.py` (`count_tokens`, `fits_in_model`,
  `MAX_CHUNK_TOKENS = 510`) + `tests/test_tokens.py` (4). `02_ingest.py` prints the largest
  chunk in tokens and how many are over the limit. 94 passed; ruff clean.

### 2026-10-17, session 17b: step 2.4 block parser

- Learner: "I forgot 2.4, implement it too".
- `src/docpilot/ingestion/blocks.py`, `tests/test_blocks.py` (7: `#` comment in code is
  not a heading, table stays one block, heading path `["A", "B"]` and reset, anchor
  removed + `#hashtag` not a heading, list with sub-items one block, blank line splits
  paragraphs, unclosed code block kept).
- Plan fixes: (1) heading anchors `{ #x }` removed; `parse_heading` is now the ONE heading
  rule, used by metadata.py too; (2) a `list` kind added (plan: lists = paragraphs) because
  q-018's answer is a bullet list that fixed chunks split; (3) a heading needs a space.
- Real pages (clean + includes): 64 headings, 256 paragraphs, 63 code blocks (= fence
  pairs), 16 lists, 0 tables (none in these 4 pages; tables tested on made-up text only);
  **0 lines lost**; q-018's answer is one `list` block under `Request Body > Results`.
- Full suite 90 passed; ruff clean. Blocks are not used by ingestion yet: the fixed
  chunker ignores them; block-based chunkers come in 2.6.

### 2026-10-17, session 17: steps 2.3 (includes) and 2.5 (metadata)

- Learner (no time) skipped the C0+clean prediction/run and asked for 2.3 and 2.5. Step
  2.4 (blocks) was not requested; 2.5's heading path is computed from a line scan of the
  text instead of from Blocks (noted; 2.4 can reuse or replace it).
- 2.3: verified paths at commit d623544: `docs_src/...` at repo root -> 200,
  `docs/en/docs_src/...` -> 404, so the marker's `../../` maps to the repo root.
  `ingestion/includes.py` (find + resolve; missing files reported, marker kept);
  `01_download_docs.py` downloads the 18 referenced files to `data/code/fastapi/`
  (gitignored, `config.CODE_DIR`); `02_ingest.py --includes`. Dry run on the 4 pages
  (clean + includes, no embedding): **includes resolved 29, missing 0**, markers left 0;
  first-steps chunk 0 now contains the real minimal-app code. Chunks 51 -> 57
  (12 + 19 + 17 + 9). 5 tests.
- 2.5: `ingestion/sources.py` (register: fastapi = docs / tutorial / commit / MIT /
  public; the download script now reads the commit from it), `Chunk` gains strategy,
  char_start, domain, technology, doc_type, version, heading_path, has_code, has_table,
  content_hash (defaults keep old code working); `ingestion/metadata.py` (heading scan
  skips code blocks and `{ #anchor }`; unknown source -> KeyError, D-030 licence rule);
  Qdrant payload = all Chunk fields. Embedded text unchanged, so C0 is unaffected. 5 tests.
- Full suite 83 passed; ruff clean; length check OK. Learner runs still pending:
  `C0+clean` (2.2) and `C0+clean+incl` (2.3), each with a one-line prediction.

### 2026-10-15, session 16: 2.1 regression check passed; step 2.2 cleaner

- Learner's run: `02_ingest.py` + `run_retrieval_eval --config-id C0-2.1` (commit
  `785120a` clean). Learner compared C0 test vs C0 dev in MLflow by mistake (n 8 vs 19).
  Mentor compared the right files: all 7 overall metrics, per-type table, and all 19
  questions' retrieved chunks/order/scores identical to C0. Only search latency differed
  (p95 2.2 -> 1.7 ms: machine timing) and the two settings labels added in 2.0.
  **Refactor regression check: passed.**
- Learner asked how to judge eval results good or bad (answered in chat; see the evals
  guide sections 9, 13, 16).
- 2.2: measured the real noise first: 144 tags, of which **114 inside ```console blocks**
  (terminal screenshot) and 30 in prose; none in python/JSON/TOML/plain blocks. **Plan
  bug:** the plan's cleaner skips every fence, so it would leave 114 of 144 tags. Fix:
  `console` fences are cleaned like prose (+ `html.unescape` for `&apos;`); every other
  fence stays exact. Tag list widened to the tags actually found (b, u, dfn, abbr, code).
- `src/docpilot/ingestion/cleaner.py`, `tests/test_cleaner.py` (7). On the 4 pages:
  tags 144 -> 0; chars 34350 -> 31720; all 30 real code blocks byte-identical (checked
  with a fence parser; a first regex check gave a false alarm and was itself wrong).
- `02_ingest.py --clean --collection docpilot_clean` (C0 collection stays intact).
  Full suite 73 passed. The eval cannot see how a collection was built: the config id
  (`C0+clean`) and collection name carry that until 2.9 records ingest settings.

### 2026-10-15, session 15: step 2.1 refactor into packages

- Learner opened MLflow (Model training -> docpilot-retrieval), compared C0 dev vs test:
  params identical except `split`; metrics equal the JSON (dev recall_at_5 0.842, mrr
  0.667; test 1, 0.635). Learner asked whether MLflow is "tracing": explained experiment
  tracking (lab notebook, per eval run) vs tracing (dashcam, per request, Phase 7).
- 2.1 moves with `git mv` (history kept): `loader.py` -> `ingestion/loader.py`,
  `chunker.py` -> `ingestion/chunkers/fixed.py` + `chunkers/base.py` (`Chunk`),
  `embedder.py` -> `embedding/dense.py`, `vector_store.py` -> `store/qdrant_store.py`,
  `llm.py` -> `llm/client.py`; `__init__.py` with a one-line docstring each (no
  re-exports: imports name the real module). 22 import lines in 13 files updated.
- Checks: no old imports left; new packages import from outside the repo (editable
  install); ruff clean; **66 passed**; scripts `--help`, `02_ingest` import, API route OK.
- Not yet done (learner's hands-on): re-ingest + `run_retrieval_eval --config-id C0-2.1`
  must give exactly the C0 dev numbers (plan: "a refactor that changes the numbers is a bug").

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

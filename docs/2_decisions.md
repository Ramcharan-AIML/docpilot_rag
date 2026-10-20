# Decision Log (part 2)

Continues [decisions.md](decisions.md) (D-001 to D-037, version pins, free-tier checks),
which reached the 500-line limit. Same format: what, why, alternative, why not.

---

## D-038: chunk sizes are measured in embedding-model tokens; limit 510 (2026-10-17)

- **What:** from step 2.6 every chunker measures size with
  `ingestion/chunkers/tokens.py` (`count_tokens`, the embedder's own tokenizer).
  `MAX_CHUNK_TOKENS = 510`. `02_ingest.py` prints the largest chunk and how many are over.
- **Verified 2026-10-17** on `BAAI/bge-small-en-v1.5` revision `5c38ec7c...`:
  `max_seq_length` 512, `tokenizer.model_max_length` 512, `max_position_embeddings` 512;
  fast `BertTokenizer` (transformers 5.18.0, sentence-transformers 6.1.0); every text gets
  `[CLS]` + `[SEP]`, so 510 tokens are left for the chunk. The 8-token query prefix only
  affects queries, not chunks.
- **Why:** text over the limit is cut off silently when embedded. Measured on the 4 cleaned
  pages: 3.07 to 3.46 characters per token, so C0's 800 characters are about 250 tokens
  (no truncation in C0). Characters cannot guarantee the limit for code-heavy chunks.
- **Alternative:** keep characters with a safety margin. **Why not:** the margin is a
  guess that breaks on code and identifiers; the tokenizer is already loaded, so exact
  counting is free.
- **Alternative:** `tiktoken` or a word count. **Why not:** a different tokenizer from the
  one the model uses; the count would not match what is embedded.
- No new dependency (the tokenizer comes with sentence-transformers).

## D-039: chunkers in Phase 2 run on cleaned text with includes resolved (2026-10-17)

- **What:** C1 to C5 are built from `--clean --includes` text. C0 stays the raw baseline.
- **Evidence (dev, n=19, fixed 800/100):** C0 R@5 0.842, MRR 0.667; C0+clean 0.947, 0.665;
  C0+clean+incl 0.895, 0.643 (see `evals/ABLATION.md`, data-quality rows).
- **Why:** cleaning has no clear downside. Includes cost about 1 question at fixed size
  (prose chunks lose rank to new code chunks), but without them the LLM cannot show real
  code, which is what "show me" questions need. A difference of 1 question is within noise.
- **Alternative:** compare chunkers on cleaned text only. **Why not:** the final system
  will include the code, so the chunker must be chosen on the text it will really see.
- **Revisit** if every block-based chunker still loses prose questions with includes.

## D-040: every collection carries a manifest; evals record it (2026-10-19)

- **What:** `02_ingest.py` writes `data/processed/collections/<collection>.json` (strategy,
  size, overlap, unit, cleaned, includes, chunk count, largest chunk in tokens).
  `evals/common.base_record` reads it, so result files and MLflow params show the real
  build settings; `settings_source` says `manifest` or `config.py` (old collections).
- **Why (plan bug):** results took chunk settings from `config.py`, so a "recursive 400"
  run would have been recorded as "fixed 800/100". With one collection per strategy, the
  settings belong to the collection, not to the config file.
- **Alternative:** read settings from the Qdrant payload. **Why not:** the payload holds
  per-chunk facts (strategy, but not size, overlap or cleaning flags); copying build
  settings into every point wastes space. **Alternative:** put them in the config id.
  **Why not:** a typo in a name cannot be checked; a file written by the ingest can.
- No new dependency (json from the standard library). Manifests are gitignored like the
  index itself; both are rebuilt by `02_ingest.py`.

## D-041: how the six chunkers are built (2026-10-19)

- **One span model for all:** every chunker cuts the document at (start, end) character
  positions, so `Chunk.text` is always an exact slice (0 characters lost and 0 bad slices
  on the 4 pages, every strategy). Blocks (2.4) gained `start`/`end` for this.
- **`Chunk.prefix`** (new field, embedding only) holds the heading path (hierarchical), the
  question (Q&A pieces) or the LLM note (contextual). The plan's `display_text` became the
  normal `text`; one field instead of two copies of the text.
- **C1 recursive is text-based** (plan separators, like LangChain); **C4 hierarchical is
  the structure-aware one** (blocks, heading always starts a chunk, code/table/list never
  split: 0 of 79 split on the real pages). The size counts the text only, so C4 with and
  without prefix make the same 65 chunks and differ in one thing.
- **C3 parent-child:** parent = hierarchical group up to 800 tokens (62 parents, median
  164, max 616); children 128 tokens (131). Parents in
  `data/processed/parents_<collection>.json`. **Plan change:** no `--parent-store` flag;
  the eval reads `parents_file` from the manifest (D-040) and scores parent text,
  fetching 30 children to keep 10 distinct parents. Known gap: `rag.ask()` does not lift
  to parents yet; wire it in only if C3 wins (2.9).
- **C2 semantic:** units = sentences, code/list/table/heading blocks whole; percentile 10
  (dry run: 25 -> 119 chunks median 44; 5 -> 50 median 320; 10 -> 64 median 174, the
  same size as C4). Weakness seen: 15 chunks under 20 tokens.
- **C5 contextual:** base = hierarchical (changeable with `--base`). **Verified
  2026-10-19 from Groq response headers:** gpt-oss-120b and gpt-oss-20b both 8000 tokens
  per minute, 1000 requests per day. So the prompt holds the chunk's level-1/2 section
  (max 1500 tokens), not the whole page (about 4000 tokens = 2 calls a minute). Cache
  key = sha256(prompt version | model | source | chunk text). Calls, cache hits, 429
  retries and seconds go into the manifest.
- **Q&A pairs:** `### Q3.` or `**Q:**` starts a pair; the next question or a higher heading
  ends it. On `docs/interview/phase_1_interview.md`: 15 pairs -> 15 chunks + 1 intro.
- **Tokenizer fact found by a test:** a "word" over 100 characters becomes ONE `[UNK]`
  token, so its content is invisible to the model.
- **Alternatives:** LangChain/LlamaIndex splitters. **Why not:** Rule 8 (raw first); the
  comparison with LangChain's splitter is optional and needs its own decision entry.

## D-042: provisional chunking leader = C4-200, hierarchical + heading prefix (2026-10-19)

- **Evidence (golden v0, dev, n=19, commit `509d687`):** C4-400 R@1 0.737, R@5 0.842,
  MRR 0.795; C4-200 R@1 0.684, R@5 0.895, MRR 0.782 (a tie: within 1 question).
  C1-400 R@1 0.526, MRR 0.679; C3-128 0.579, 0.696; C2-400 0.316, 0.537; C0+clean+incl
  0.474, 0.643. LLM context p50: C4-200 575 tokens, C4-400 1011, C0 1013.
- **Why C4-200:** ties on quality with C4-400; about 43% fewer tokens per question means
  a faster LLM step (the LLM was about 96% of C0's latency) and fewer 429s under Groq's
  8000 tokens/minute. Search time is about 2 ms for every config, so it does not decide.
- **Not final:** the plan picks the winner in 2.9 on golden v1 (about 60 questions, three
  domains), then runs the test split once. Before that: latency and abstention for
  C4-200 vs C0 (both runners now take `--collection`). Smaller context could also drop
  facts the LLM needs; answer quality (faithfulness) is measured in Phase 3.9.
- **Alternative:** C4-400 (best R@1, MRR). **Why not now:** 1 question is noise; it costs
  76% more tokens. **Alternative:** C1 recursive (learner's guess). **Why not:** ties on
  R@5 only; 4 fewer questions at rank 1 than C4-400.
- The app still uses C0 (`docpilot_naive`) until 2.9 confirms the choice.

## D-043: Docling (slim) for PDF and DOCX; first PDF = RAGAS paper, first DOCX = own notes (2026-10-19)

- **What:** `ingestion/document_loader.py` converts .pdf/.docx to Markdown with
  `docling-slim[convert-core,format-pdf,format-docx,models-local]==2.140.0` (+
  `opencv-python-headless==5.0.0.93`), then the normal pipeline runs. OCR off, table
  structure on. Results cached in `data/processed/converted/` by sha256 + Docling version.
- **Verified 2026-10-19:** PyPI latest docling 2.140.0 (Python >=3.10). Full `docling`
  = 54 packages; slim with 4 extras = 24 packages, +89 MB in site-packages; torch stays
  2.14.1, adds torchvision 0.29.1; downgrades typer 0.27.2 -> 0.26.8 (`pip check` clean).
  API read from the installed package: `PdfPipelineOptions.do_ocr` defaults to **True**
  (we set False). **Packaging gap:** the table model imports `cv2` but its package does
  not declare it (full docling gets OpenCV only via the OCR extra); pinned explicitly.
- **Speed (this laptop, CPU):** RAGAS PDF, 8 pages: 36.4 s cold, 26.1 s warm (about
  3.3 s/page), 4 tables found; DOCX (notes): 8.0 s first time; cached re-read 0.03 s.
- **Quality seen (RAGAS):** Table 1 exact; flaws: missing spaces in some headings
  ("RelatedWork"), line-break hyphens kept ("Op- penheimer"), all headings `##` (nesting
  lost), a footnote placed inside a prompt box (reading order). Appendix tables of
  704-1463 tokens must be split (limit 510): pieces after the first lose the header row.
- **Why Docling, not PyMuPDF:** PyMuPDF is faster and smaller but gives text in reading
  order without table structure: a results table becomes loose numbers, which is what
  our table questions need. **Why not full `docling`:** 30 extra packages (OCR, OpenCV GUI,
  Excel, PowerPoint, email, code parsers) we do not use. **Why no OCR:** both files are
  digital; scanned PDFs are out of scope until a need appears.
- **Sources (licences checked on arxiv.org 2026-10-19):** RAGAS (2309.15217v2) CC BY 4.0
  -> public, group B; BEIR CC BY-SA 4.0 (candidate later); MTEB and Lost in the Middle
  arXiv non-exclusive -> would be `local_only`. DOCX: open .docx files are rare, so
  `scripts/make_notes_docx.py` builds one from the learner's own
  `docs/interview/phase_1_interview.md` + a table of real C0 numbers (own work, public,
  group C). Learner chose both (2026-10-19). Download pinned by sha256.
- **Golden v0.1:** +8 table questions (q-033 to q-040), snippets copied by code from the
  converted Markdown. `02_ingest.py --sources fastapi` rebuilds the v0 corpus exactly.

## D-044: Chain-of-Thought paper replaces the RAGAS paper as the first PDF (2026-10-20)

- **What:** `data/docs/cot/cot_2201.11903v6.pdf` (Wei et al., "Chain-of-Thought Prompting
  Elicits Reasoning in Large Language Models", arXiv 2201.11903v6, 2023-01-10,
  sha256 `7d9f878c...a72a12`) replaces the RAGAS paper. Source key `cot`, group B
  (learning), public.
- **Why (learner request):** the RAGAS *paper* in the corpus was confused with the RAGAS
  *library* (a generation-eval tool we have not installed). The learner asked for a PDF on a
  topic that is not a tool or doc of this project.
- **Licences checked 2026-10-20 on arxiv.org:** Chain-of-Thought CC BY 4.0 (chosen);
  LoRA, Attention Is All You Need, Dense Passage Retrieval: arXiv non-exclusive (would be
  `local_only`).
- **Docling on it:** 43 pages, 8 tables found, 182.4 s (about 4.2 s per page, CPU); Table 2
  (GSM8K etc. by model size) and Table 4 (commonsense) come out as clean rows; each
  "Table N:" caption sits right above its table. Table 1 has merged cells
  ("Standard Chain of thought + ext. calc" in one column).
- **Golden v0.2:** RAGAS questions q-033..q-036 removed; q-041..q-044 added (3 dev, 1
  test) with snippets = one exact, unique table row. New ids, so results of v0.1 and v0.2
  can never be mixed up. Notes DOCX questions q-037..q-040 unchanged.
- **Alternative:** BEIR (CC BY-SA 4.0). **Why not:** retrieval benchmarks are close to what
  this project does, so it could cause the same kind of confusion.

## D-045: corpus v1 (three domains, 20 documents) and golden set v1 (65 items) (2026-10-20)

- **Register:** kept in `src/docpilot/ingestion/sources.py` (grown from step 2.5), not the
  plan's `scripts/doc_sources.py`: ingest, metadata and downloads must read ONE list. New
  fields: topic, url, licence_url, checked date. `tests/test_sources.py` fails if any entry
  lacks licence, licence link, visibility, domain, version or a valid check date.
- **Sources (all public; licences checked 2026-10-20):** docs = FastAPI (4 pages, MIT),
  Pydantic concepts config/strict_mode/alias (MIT, commit 471fe56), Docker get-started
  concepts, 5 pages (Apache-2.0, commit 95b8ec6); learning = Chain-of-Thought PDF (CC BY
  4.0) + Wikipedia "Retrieval-augmented generation", "Word embedding", "Evaluation measures
  (information retrieval)" (CC BY-SA 4.0, revisions 1381095247 / 1374850731 / 1375531235);
  interview = the learner's `docs/interview/phase_0/2/3_interview.md` + phase 1 Word file.
  Later interview files cover phases not built yet, so they are not indexed.
- **Wikipedia:** plain-text extracts API (no wiki markup); headings `== X ==` -> `## X`;
  each formula arrives as ~60 lines of loose symbols + one LaTeX line: only `$LaTeX$` kept
  (evaluation-measures article 28 KB -> 13 KB). The API serves only the latest revision, so
  the download stops if a pinned revision changed (snippets must be re-checked).
- **TLS:** Python's default certificate store on this laptop rejected Wikipedia
  ("certificate has expired") while the site's certificate is valid until 2027-01-02;
  downloads use `certifi`'s CA bundle (already installed with requests; no new package).
- **Cleaner (Docker/Hugo):** YAML front matter -> `# Title`; shortcodes removed, tab names
  kept ("Using the CLI:"). FastAPI pages contain neither (checked), so earlier rows are not
  affected. Pydantic MkDocs markers (`!!! note`, `=== "tab"`) kept: short and readable.
- **Golden v1 (`evals/golden/VERSION`):** 65 items = 46 dev + 19 test; docs 41 (5
  unanswerable), learning 12 (1), interview 12 (1). New field `domain` (where the answer
  lives; must match the register entry of the evidence document); new types `concept` and
  `interview`. 25 new questions; every snippet checked by code against the converted text.
- **Correction:** q-003 ("status code on validation failure") was `not-in-docs`, but the
  phase 1 Word notes (added in 2.7) say "422". Now answerable, domain interview. Missed in
  2.7: adding documents must always re-check every unanswerable question.
- **Imbalance seen:** with C4-200 the CoT PDF gives 364 of 733 chunks (its long appendix).

## D-046: step 2.9 tooling: matrix runner, generated ablation block, fair control rows (2026-10-20)

- **What:** `scripts/run_chunking_matrix.py` runs, per config, the same two commands a human
  types (`02_ingest.py`, then `python -m evals.run_retrieval_eval --ablation`), skips configs
  already scored on the current commit + golden version, refuses uncommitted code, and ends
  with `python -m evals.make_ablation`. That script writes the main, per-type and per-domain
  tables between `<!-- make_ablation:start/end -->` markers in `evals/ABLATION.md`.
- **Matrix on golden v1 (dev):** C0-v1 (raw, frozen baseline), **FT-200-v1 and FT-400-v1**
  (fixed-size tokens WITH clean + includes: the fair control, so C1-C4 differ from it in
  chunking only), C1-200/400, C2-400, C3-128, C4-200/400, C4-400-noprefix, QA-400. C5
  contextual only with `--with-llm` (1 LLM call per chunk; 733 chunks would use most of the
  Groq free daily request limit of 1000, D-041).
- **Plan fixes:** (1) the plan's `python evals/run_retrieval_eval.py` must be `python -m
  evals.run_retrieval_eval` (D-036); (2) "ABLATION.md generated" = the tables block only:
  the hand-written history (v0 rows, readings) stays, because it cannot be regenerated.
- **Also changed:** `02_ingest.py` stores `ingest_seconds` in the manifest (plan's "ingest
  minutes" column); MLflow de-duplication now keys on results file **and** git commit, so a
  same-day re-run after a code change is a new run instead of being skipped silently.
- **Numbers come from the JSON** each MLflow run points to (results_file tag), the committed
  source of truth; MLflow selects which runs (ablation=true). Fallback without MLflow: all
  result files of that golden version, and the output says so.
- **Alternative:** one Python process that imports and loops. **Why not:** a second code
  path that could disagree with the manual commands, and local Qdrant locks per process.
- **Alternative:** generate the whole ABLATION.md. **Why not:** loses the readings and the
  v0 history that explain the numbers.
- No new dependency.

## D-047: default chunking = FT-200 (fixed 200 tokens, overlap 25, cleaned, includes) (2026-10-20)

- **What:** the app, `03_ask.py` and the evals use collection `docpilot_v1_ft200` by default
  (`config.COLLECTION_NAME`; build command in `config.INGEST_COMMAND`). `02_ingest.py` now
  requires `--collection`, so a bare run cannot overwrite the app's index with C0 chunks.
- **Evidence (golden v1, dev, n=41, commit `f4a3a49`, clean; matrix of 11 configs):**
  R@5 in questions: C3-128 35, C1-400 34, QA-400 34, C4-400 33, **FT-200 33**, C0 32.
  The top five are within 2 questions = a tie (1 question = 0.024). Tie-breakers (teaching
  note part 11): MRR also tied (C4-400 .729, C3 .717, C1-400 .705, FT-200 .701); context
  sent to the LLM is smallest for FT-200 (4 x 200 tokens max, by construction); simplest.
  The dirty run (`3778c0f+dirty`) gave identical numbers for every config.
- **Test split, run once (n=17, `f4a3a49`):** FT-200 R@1 .471 (8), R@5 .882 (15), MRR .620;
  C0 R@1 .353 (6), R@5 .941 (16), MRR .608. FT-200 does **not** beat C0 on recall.
  Dev + test (58): R@5 48 vs 48; R@1 34 vs 28. Honest claim: **a ranking gain, not a
  recall gain**; chunking strategies are mostly within noise at this golden-set size.
  C2 semantic was clearly worst (MRR .574).
- **Alternative:** C3-128 parent-child (best dev R@5 .854). **Why not:** inside the noise
  band; sends whole parents (up to 800 tokens each, about 2-4x FT-200's context) into
  Groq's 8000 tokens/minute; needs a parents file next to the index.
- **Alternative:** keep C0. **Why not:** same recall, worse ranking, character sizes can
  approach the 510-token limit (largest 434), raw text without the real code.
- **Re-check, planned:** at the end of Phase 3 (hybrid + reranker), re-run FT-200, C3-128
  and C4-400 through the final pipeline (`run_chunking_matrix.py --only ...` + the Phase 3
  eval). Switch only if one beats FT-200 by 3 or more questions. Also re-check after a large
  corpus change (golden v2) or an embedding-model change. Frozen from Phase 4 on.

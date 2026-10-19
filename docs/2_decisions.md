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

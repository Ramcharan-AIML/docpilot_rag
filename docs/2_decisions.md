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

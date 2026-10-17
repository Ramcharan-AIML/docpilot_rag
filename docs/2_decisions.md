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

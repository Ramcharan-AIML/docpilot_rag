# DocPilot User Guide (Part 2)

Continues [USER_GUIDE.md](USER_GUIDE.md), which hit the 500-line limit (Rule 12). Part 1
holds the project overview, Phase 0, steps 1a.1 and 1a.2, daily commands and the concept
table. Phase 1 steps from 1a.3 on are written here.

---

## 16. Step 1a.3: `chunker.py`, fixed-size chunks with overlap (2026-10-12, not yet committed)

**Goal:** cut each document into pieces of `CHUNK_SIZE` characters (800), each starting
`CHUNK_SIZE - CHUNK_OVERLAP` (700) characters after the previous one. Deliberately naive
(D-006): it cuts through words and code. Phase 2 measures how much that hurts.

**Files:** `src/docpilot/chunker.py`, `tests/test_chunker.py`.

**Changed from the plan:** defaults read from `config` (no second copy of 800/100); new
"no text is lost" test (rebuild the input from the chunks); `itertools.pairwise` for
neighbour pairs (ruff B905).

**Real results** (36-character text `a..z0..9`, `chunk_size=10`, `overlap=3`, step 7):
| Chunk | Start | Text | Length |
|---|---|---|---|
| 0 | 0 | `abcdefghij` | 10 |
| 1 | 7 | `hijklmnopq` | 10 |
| 2 | 14 | `opqrstuvwx` | 10 |
| 3 | 21 | `vwxyz01234` | 10 |
| 4 | 28 | `23456789` | 8 |

`pytest tests/test_chunker.py -v`: 9 passed (5 tests + 1 test run with 4 bad settings).

| Prediction | Yours | Real |
|---|---|---|
| Number of chunks | 5 | 5 (correct) |
| Last chunk | `23456789`, 8 chars | `23456789`, 8 chars (correct) |
| Why 8 | "due to the overlap" | half right: overlap decides where it **starts** (28 = 4 x 7); the **text running out** decides the length (36 - 28 = 8) |
| Pad the last chunk to 800? | add dummy characters | no: see lessons |

**Lessons:**
1. Chunk length = `min(chunk_size, characters left after start)`. Overlap only moves the
   start. Homework: predict the last chunk for `fixed_size_chunks(t, "a.md", 10, 0)`,
   then run it.
2. Never pad text with dummy characters. The embedding turns *all* the text into meaning,
   so `"...0000000"` drags the vector toward "zeros"; the LLM also reads the padding and it
   costs tokens. Models accept any length up to 512 tokens. The tokenizer pads *inside* the
   model with `[PAD]` tokens and an attention mask tells the model to ignore them. Padding
   is the model's job, not ours.
3. The real last-chunk problem is the opposite: a **tiny tail**. At 800/100 the last chunk
   of a long document can be as short as 101 characters, and 100 of those are repeated
   from the previous chunk. Fixes (Phase 2 ideas): merge a short tail into the previous
   chunk, or chunk by headings/sentences.
4. `[10-10]`, `[0-0]` in test names come from `@pytest.mark.parametrize`: one test
   function, run once per settings pair.

**New concepts:** chunk, overlap, step, tail chunk, parametrized tests, attention mask.

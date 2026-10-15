# Teaching Notes, Phase 2: Ingestion Quality and Chunking

Plan file: `docs/implementation_plan/phase_2_chunking.md`

**New in this phase:** MLflow experiment tracking (step 2.0, read `primer_mlflow.md`) and the
CI eval gate (step 2.10, `primer_evals.md` section 8 and `primer_git_workflow.md` section 8).

---

## 1. "Garbage in, garbage out" for RAG

**Like I'm five:** if the library shelves hold books with missing pages and coffee stains,
the best librarian in the world still hands you a stained book.

**What it really is:** retrieval can only find what ingestion stored. Phase 1 showed three
data problems (code replaced by include markers, HTML colour tags, chunks cut mid
structure). Fixing data is often the **cheapest big win** in a RAG system, bigger than any
clever retrieval trick. That is why Phase 2 comes before hybrid search.

**Why measure cleaning separately** (`C0+clean`, `C0+clean+incl`): so in an interview you
can say exactly how much data quality alone gave, versus how much chunking gave.

---

## 2. The ingestion pipeline as an assembly line

```text
loader ─▶ cleaner ─▶ includes ─▶ blocks ─▶ metadata ─▶ chunker ─▶ embed ─▶ store
```

Each station does one job and has its own test. If an answer is wrong you can check each
station's output to find where the damage happened.

**Why no LLM here (except contextual chunking):** parsing and cutting are deterministic
tasks. Code is free, fast, repeatable, and testable. An LLM would be slower, cost tokens,
and might give a different result each run. Knowing where **not** to use an LLM is a
senior-engineer signal (architecture section 6).

---

## 3. The refactor: same numbers or it is a bug

Moving files into packages (`ingestion/`, `embedding/`, `store/`) should change **nothing**
about behaviour. Re-running C0 and getting the exact same numbers proves it. If numbers
change, something changed by accident. This habit (check that a refactor is
behaviour-neutral) is exactly what CI does automatically in Phase 7.

---

## 4. Cleaning without breaking code

The cleaner removes HTML tags from prose but **never** touches lines inside ``` fences.
Why: code must stay exact. `<div>` inside a code example is real content, a user may be
asking about it. The cleaner walks line by line and keeps an `inside_code` flag, switching
it each time it sees a fence.

---

## 5. Resolving includes

FastAPI docs write `{* ../../docs_src/first_steps/tutorial001_py310.py *}` instead of the
code. The real code lives in a separate file. Our resolver finds each marker with a regular
expression, opens the file, and puts the code in its place as a fenced block. Missing files
are **reported**, not silently skipped: silent failures are how data pipelines rot.

---

## 6. Parsing into blocks

**Like I'm five:** before cutting a newspaper into clippings, you first see where each
article, photo, and table starts and ends, so you never cut a photo in half.

`blocks.py` labels every part of a page: heading, paragraph, code, table. It also tracks
the **heading path** (`["Query Parameters", "Optional parameters"]`), which tells every later
step where a piece sits in the document. Chunkers then work with whole blocks.

---

## 7. Tokens vs characters, and the silent truncation trap

Phase 1 measured size in characters. Models read **tokens**. One token is roughly a word
piece; code often has more tokens per character than prose (symbols, short names).

**The trap:** every embedding model has a maximum input length (check the model card).
Text longer than that is **cut off without any error**: the end of your chunk is simply
not in the vector. A "bigger chunks did worse" result may really be "bigger chunks were
truncated". So in Phase 2 we count sizes with the embedding model's own tokenizer and only
test sizes that fit.

---

## 8. The six chunking strategies

Picture one long docs page with headings, paragraphs, a code block, and a table.

### 8.1 Fixed-size + overlap (baseline)
- **Like I'm five:** cutting a cake every 5 cm, whatever is in the way.
- **Good:** simplest, predictable sizes. **Bad:** cuts code, tables, sentences in half.

### 8.2 Recursive
- **Like I'm five:** cut at chapter breaks first; if a piece is still too big, cut at
  paragraph breaks; then sentences; then words, only if you must.
- **How:** a priority list of separators: headings, blank line, newline, ". ", space.
- **Good:** respects natural boundaries. **Bad:** does not really know about code/tables.
- **Why write it ourselves:** after ours works, compare with LangChain's version. Being able
  to say "I wrote the recursive splitter and compared it with LangChain's" beats "I called
  a function".

### 8.3 Semantic
- **Like I'm five:** read sentence by sentence, and start a new piece whenever the topic
  changes.
- **How:** embed each sentence; compute cosine similarity between neighbours; where
  similarity drops sharply (below a percentile), cut.
- **Good:** chunks follow topics. **Bad:** slower (embeds every sentence); the threshold
  needs tuning; docs pages are often already one topic per section, so it may not beat
  heading-based splitting. We find out by measuring.

### 8.4 Parent-child (small-to-big)
- **Like I'm five:** a book index points you to the exact line (small, precise), but you
  read the whole page around it (big, full context).
- **How:** index small **child** chunks (precise search), but give the LLM the bigger
  **parent** section that the child came from.
- **Good:** precise matching **and** rich context. **Bad:** extra storage and logic; the
  LLM gets more text (more tokens).
- **Eval detail:** a hit is checked in the parent text, because that is what the LLM sees.

### 8.5 Hierarchical / structure-aware
- **Like I'm five:** cut along the lines the author already drew: chapters and sections.
- **How:** group blocks under their heading up to a size limit; never split code or table
  blocks; prepend the heading path to the chunk text, so a chunk that only says
  "set it to None" still carries "Query Parameters > Optional parameters".
- **Good:** usually the best fit for documentation. **Bad:** depends on good parsing; a
  huge code block can exceed the size limit (decide: keep whole and accept the size, or
  split at blank lines inside the code; record your choice).

### 8.6 Contextual
- **Like I'm five:** before filing a torn-out page, write a sticky note on it: "this is from
  the FastAPI tutorial, section on query parameters, explaining defaults".
- **How:** an LLM reads the whole document and one chunk, and writes 1-2 sentences of
  context. We prepend that note before embedding (and before BM25 in Phase 3).
- **Good:** fixes chunks that make no sense alone. **Bad:** one LLM call per chunk at
  ingestion. On free tiers that means rate limits and time, so we **cache** every result by
  hash; re-runs cost nothing.
- **We keep `display_text`** (the chunk without the note) so citations show the real doc text.

---

## 9. Metadata: labels on every chunk

| Field | Used for |
|---|---|
| `source`, `chunk_number` | Citations |
| `heading_path` | Context in the chunk text; nicer citations |
| `technology`, `version`, `doc_type` | Filters (Phase 3): "only Docker docs" |
| `has_code`, `has_table` | Per-type analysis; routing table questions to SQL (Phase 5) |
| `content_hash` | Dedupe; incremental ingestion (Phase 7) |

Metadata is cheap to add now and expensive to add later (re-ingest everything).

---

## 10. Thinking like an experimenter (ablation)

**Ablation** = turn one thing on or off and measure the change. Rules:

1. **Change one thing at a time.** If you change chunk size and strategy together, you
   cannot tell which one helped.
2. **Same exam for every row.** All rows in one table use the same golden version and split.
   When the golden set grows, re-run the old rows.
3. **Look per type, not just the average.** Code questions may prefer hierarchical, prose
   questions may prefer recursive. That is a finding.
4. **Record the cost too:** chunk count, ingest time, LLM calls. A small gain for 10x cost
   may not be worth it.
5. **Test split once at the end** for the winner, to check you did not overfit to dev.
6. **Small datasets are noisy.** With 60 questions, one question = 1.7 percentage points.
   Treat tiny differences as ties. Say this honestly in interviews.

---

## 11. Docling (step 2.7)

Docling converts PDFs and HTML into structured Markdown, understanding layout (columns,
tables, headings). We feed its output into the **same** blocks pipeline, so one pipeline
handles many input formats.

**Why not PyMuPDF:** faster and lighter, but it extracts mostly plain text and is weaker on
tables. **Why not a hosted parser:** limits or cost, and data leaves the machine. Docling
downloads layout models and is heavier on CPU, so we verify its size and speed first.

---

## 12. Common mistakes

- Editing code inside fences while "cleaning".
- Comparing strategies on different golden versions.
- Forgetting that chunk size in characters is not tokens.
- Declaring a winner from a 1-question difference.
- Letting contextual chunking re-run LLM calls every ingest (no cache).
- Silently skipping missing include files.

---

## 13. Self-check

1. Why fix data before improving retrieval?
2. Why must a refactor give identical eval numbers?
3. Explain all six strategies with an analogy each, and one weakness each.
4. Why does parent-child evaluation check the parent text?
5. What is silent truncation and how did you avoid it?
6. What does contextual chunking cost, and how did you control the cost?
7. Which strategy won on your data, by how much, and for which question types?

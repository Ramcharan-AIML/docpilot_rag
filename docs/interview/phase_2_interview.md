# Interview Questions, Phase 2: Data Quality and Chunking

---

### Q1. "What chunking strategy did you use and why?"

**Testing:** do you have evidence or just an opinion.

**Model answer (C-A-E-T):** "I compared six strategies on the same golden set: fixed-size,
recursive, semantic, parent-child, hierarchical, and contextual, at several sizes, each in
its own Qdrant collection. [Winner] won with Recall@5 [n/a] vs [n/a] for the baseline, and
MRR [n/a]. Per question type, [e.g. code questions] preferred [strategy]. The trade-off was
[ingest cost / complexity], so I chose [strategy] as the default."

**Losing answer:** "Recursive with 512 tokens, it's the standard."

---

### Q2. "Explain parent-child chunking."

**Model answer:** "Search small, answer big. Small child chunks give precise matches; the
LLM gets the larger parent section for context. I indexed children, stored parents
separately keyed by `parent_id`, and in the eval I checked the gold snippet against the
parent text, since that is what the LLM sees."

**Follow-up:** "Downside?" "More tokens per prompt, extra storage and logic, and two children
from the same parent must be de-duplicated."

---

### Q3. "What is contextual chunking, and what did it cost?"

**Model answer:** "An LLM writes one or two sentences placing each chunk in its document,
like 'This section of the FastAPI tutorial explains optional query parameters'. I prepend
that before embedding and keyword indexing. Chunks that make no sense alone become
findable. Cost: one LLM call per chunk at ingestion, [n/a] calls and [n/a] minutes for my
corpus on a free tier. I cached results by hash so re-runs cost zero. The gain was [n/a]."

---

### Q4. "How did you fix data quality, and how much did it matter?"

**Model answer:** "Three fixes: strip HTML noise outside code blocks, resolve include markers
by fetching the referenced code, and parse Markdown into blocks so code and tables are never
split. I measured each separately: cleaning alone gave [n/a], includes gave [n/a]. Data fixes
were among the cheapest wins in the whole project." (Only say that last sentence if your
numbers show it.)

---

### Q5. "How do you choose chunk size?"

**Model answer:** "By measuring, in tokens of the embedding model, not characters. Too big
blurs the vector and may be truncated at the model's max length; too small loses context.
I tested [sizes] and [size] won on [metric]. I also checked that no chunk exceeded the
model limit, because truncation is silent."

---

### Q6. "Why does your parser not use an LLM?"

**Model answer:** "Parsing and chunking are deterministic tasks. Code is faster, free,
repeatable, and testable. An LLM there would add cost, latency, and run-to-run variation for
no gain. I use LLMs only where judgment is needed: contextual notes at ingestion, and
routing, grading, and generation at question time."

---

### Q7. "How did you make sure a refactor did not break anything?"

**Model answer:** "When I moved the flat modules into packages, I re-ran the C0 eval and
required exactly the same numbers. Same inputs and same model should give identical
results. Later, CI automated that check with the retrieval eval gate."

---

### Q8. "Did semantic chunking help? People say it's the best."

**Model answer:** "On my data: [result: n/a]. Documentation is already organised by
headings, so heading-based chunking captures topic changes for free, while semantic
chunking embeds every sentence and needs a tuned threshold. Whatever it showed, I kept the
decision tied to the number, not the hype."

---

### Q9. "Your golden set changed during the phase. How did you keep comparisons fair?"

**Model answer:** "Every result file records the golden-set version. When I grew the set, I
re-ran the old configurations on the new version, so all rows in one table share the same
exam. Comparing across versions would be comparing different tests."

---

### Q10. "How do you handle code blocks and tables in chunking?"

**Model answer:** "The parser labels them as blocks and the chunkers never split them.
Huge code blocks are [kept whole / split at blank lines; your decision], recorded in the
decision log. Tables are also loaded into DuckDB in Phase 5 for exact lookups, because
vector search over flattened tables is weak at counting and exact matching."

---

### Q11. Trap: "Why not just use LangChain's text splitters?"

**Model answer:** "I did use one, as a comparison. I wrote my own recursive splitter first so
I understood the algorithm, then ran LangChain's on the same docs and compared chunk
counts and scores: [n/a]. In production I would use whichever is simpler to maintain if
scores tie. Knowing what it does inside lets me debug it when it misbehaves."

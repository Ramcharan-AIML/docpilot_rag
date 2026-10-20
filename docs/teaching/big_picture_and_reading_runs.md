# The Big Picture, and How to Read Every Run

Written 2026-10-20, after your first two runs on golden v1 (commit `474161b`).
Read it top to bottom once. Then keep it open next to the terminal whenever you run something.

Parts:

1. What DocPilot is, in one breath
2. The two halves of a RAG system (what happens first, second, third)
3. The project flow: phases 0 to 8, and where evals come in
4. The golden set: the exam paper
5. The ablation idea: change one thing, re-score
6. Reading the ingest output, line by line
7. Reading the eval table, column by column
8. Latency: what the numbers mean and how to judge them
9. Today's story: what your two runs actually say
10. The end point of every run: 6 questions to ask
11. How we pick a winner (the decision rule)
12. Where we are, what comes next
13. Self-check

---

## 1. What DocPilot is, in one breath

DocPilot answers questions about **our own library** of documents: tech docs (FastAPI,
Pydantic, Docker), learning material (the Chain-of-Thought paper, Wikipedia pages) and your
interview notes. Every answer must come **from those documents**. If the answer isn't
there, it must say "I could not find this".

The real goal is bigger than the app. You should be able to say in an interview: *"I
improved it step by step, and **I have numbers** for every step."* Every table you see in
the terminal exists for that sentence.

---

## 2. The two halves of a RAG system

**Like I'm five.** Think of an open-book exam.

- **Before the exam (offline):** you cut your textbook into index cards, write a "meaning
  code" on each card, and put them in a box sorted by code. You do this **once**.
- **During the exam (online):** you read a question, find the 4 cards that best match it,
  and write your answer **using only those cards**.

If the right card isn't among your 4, even a genius can't answer well. **So the card
step (retrieval) caps the quality of the whole system.** That's why we measure it so
carefully.

**The precise version.** Here are the steps in the order they run:

```
OFFLINE: "ingestion"   (scripts/01_download_docs.py, scripts/02_ingest.py)
  1. download     get the 20 documents (data/docs/)
  2. convert      PDF / Word -> text (Docling, step 2.7)
  3. clean        remove HTML noise, front matter, shortcodes (step 2.2)
  4. CHUNK        cut each document into pieces   <-- Phase 2 tunes THIS
  5. embed        each chunk -> 384 numbers (bge-small)
  6. store        save vectors + text in Qdrant (one "point" per chunk)

ONLINE: "question time"   (src/docpilot/rag.py, the API)
  7. embed the question (with the query prefix)
  8. RETRIEVE     find the closest chunks         <-- Phase 3 tunes THIS
  9. build prompt question + top 4 chunks
 10. GENERATE     the LLM (Groq) writes the answer
 11. guard        refuse if the answer isn't in the chunks (later: guardrails)
```

So to your question "is it retrieval first, then chunking?": **No. Chunking comes first**
because it builds the box of cards. Retrieval comes later, when it searches that box. The
phases follow the same order: Phase 2 makes good cards, Phase 3 makes the search smarter.

**Why tune chunking before retrieval?** If the cards are cut badly (an answer split in
half, a heading separated from its text), a smarter search still finds bad cards.
Fix the cards first, then the search.

---

## 3. The project flow: phases 0 to 8

Each phase adds **one layer**. After each layer we run the **same exam** (golden set) and
write the score into **one table** (`evals/ABLATION.md`). The ladder of configs C0, C1,
C2... is that table.

| Phase | What we build | Question it answers | Ablation rows |
|---|---|---|---|
| 0 | Setup, embeddings, cosine similarity | "How does meaning search work?" | none |
| 1 | Naive RAG end to end + **first golden set + first evals** | "Does it work at all, and how well?" | **C0** = the baseline |
| **2 (now)** | Clean data, 6 chunking strategies, bigger corpus, golden v1, CI eval gate | "What is the best way to cut the cards?" | C1 to C5 |
| 3 | Hybrid search (BM25 + vectors, RRF), reranker, query rewriting | "How do we find the right cards better?" | C6 to C8 |
| 4 | Agent: grade the cards, rewrite the question, try again | "Does a loop beat one search?" | C9 |
| 5 | Multi-agent, tools, human in the loop | "Do tools help?" | C10 |
| 6 | Guardrails (injection, PII, unsafe output) | "Is it safe, and what does safety cost?" | C11 + safety table |
| 7 | Production: API, Docker, CI/CD, AWS, then Oracle | "Can real users use it, fast and cheap?" | latency/cost rows |
| 8 | Stretch (GraphRAG, ColBERT...) | optional extras | optional |

**Where do evals come in?** Not once at the end. **At every phase, from Phase 1 on.**
That's why the rule says "no agents, guardrails or deployment before evals exist". Without
the exam you can't tell whether a new layer helped or hurt.

```
 build a layer -> run the SAME exam -> write a row -> compare with the row above
       ^                                                       |
       +------------ keep it if it helped, drop it if not -----+
```

---

## 4. The golden set: the exam paper

**Like I'm five.** A teacher writes an exam **and** the answer key **before** grading
anyone. The golden set is our exam and answer key.

**What it really is.** `evals/golden/dev.jsonl` and `test.jsonl`, one question per line.
Each line holds:

- `question`: what a user might ask
- `evidence`: **which document** and **which sentence (snippet)** contain the answer. This
  is the answer key for retrieval.
- `should_answer`: false for trick questions whose answer is not in our documents
- `type` (factual, how-to, table-or-code...) and `domain` (docs, learning, interview), so
  we can see **where** the system is weak, not just how weak it is overall

**How a question is marked.** For each question the eval fetches the top 10 chunks. A chunk
counts as a **hit** if it comes from the right document and contains at least 70% of the
gold snippet (`evals/matching.py`, D-010). The result is a 0/1 list such as
`[0, 1, 0, 0, 0, ...]`, which means "the 2nd chunk was the right one". Every metric is
computed from that list.

**Why is `n` 41 and not 46?** Dev has 46 questions, but 5 are trick questions
(`should_answer: false`) with no evidence. Retrieval can't be marked on them because there is
no right card. They're marked later by the **abstention** check ("did it correctly
refuse?").

**Dev vs test split.**

- **dev (46)** is your **practice exam**. Run it as often as you like and tune on it.
- **test (19)** is the **final exam**. Run it **once**, only for the winner and C0.
  If you tune on test, you learn the answers by heart and your score stops meaning
  anything. That's called overfitting to the test set.

**Why "golden v1" and not v0?** We added 16 documents and changed the questions. A new exam
means **old scores can't be compared with new ones**. C0 scored 0.842 R@5 on v0 and 0.78
on v1, but **the system didn't get worse**: the exam got bigger and harder. That's why
we **re-ran C0** today: every new exam needs its own baseline.

---

## 5. The ablation idea: change one thing, re-score

**Like I'm five.** You're baking a cake and it tastes better. Was it the sugar or the oven?
If you changed both, you can't know. **Change one thing per bake.**

**What it really is.** An *ablation* compares configs that differ in **one setting**. The
row label (C0, C4-200, ...) names the config. The `What changed` column says what the one
change was.

**Honest catch about today's two runs.** C0-v1 and C4-200-v1 differ in **three** things,
not one:

| | C0-v1 | C4-200-v1 |
|---|---|---|
| chunking | fixed 800 characters, 100 overlap | hierarchical, 200 tokens, heading prefix |
| cleaned | False | True |
| includes (real code pasted in) | False | True |

That's by design. **C0 is frozen as "the naive system"**, the starting line we measure the
whole project against. But it means **C0 vs C4 isn't a pure chunking test**. In step 2.9 the
matrix adds a **control row** (fixed chunks **with** cleaning + includes) so the chunking
comparison is fair. Remember the cake.

---

## 6. Reading the ingest output, line by line

Your run of `python scripts/02_ingest.py --collection docpilot_v1_c0`:

```
cot/cot_2201.11903v6.pdf: 144815 characters -> 207 chunks
docker/persisting-container-data.md: 6896 characters -> 10 chunks
...
```

**One line per document: its size in, its number of chunks out.** What to look for:

- **Does anything look odd?** A document with 0 chunks means it failed. A huge
  document means it will dominate the index.
- **The CoT PDF is half the library.** C0: 207 of 441 chunks (47%). C4-200: 364 of 733
  (50%). The worry is that a "loud" document could crowd the top results for unrelated
  questions. **We checked:** across the top 5 of every non-learning question, CoT chunks
  showed up **3 times out of 165 slots** in C0 and **0 of 165** in C4-200. So no problem
  today. Keep watching it as the corpus grows.
- **The same document gets different sizes in the two runs.** For example,
  `fastapi/body.md` is 6611 characters raw but 8132 with includes, because the real code
  examples were pasted in. `docker/...` gets *smaller* after cleaning because the front
  matter and shortcodes were removed. This shows that cleaning and includes did their jobs.

```
Loading weights: 100% ... 199/199
```
The embedding model (bge-small) is loading from disk. 199 is the number of weight tensors
in the file. **Nothing to judge here.**

```
Warning: You are sending unauthenticated requests to the HF Hub ...
```
Hugging Face asks you to log in for higher download limits. The model is already cached,
so **ignore it**. A token isn't needed.

```
chunk tokens (prefix included): largest 434, median 205, over the 510-token limit: 0
```
**This is an important safety line.** bge-small only reads the first 510 tokens of a
chunk (D-038). Anything past that is **silently cut off**: it's stored but never searchable.
**`over the 510-token limit: 0` must always be 0.** Median 205 vs 120 also tells you C0
cards are bigger than C4-200 cards.

```
Batches: 100% ... 14/14 [00:33<00:00, 2.42s/it]
```
Embedding in batches of 32 chunks: 441 / 32 = 14 batches, about 2.4 s each on your CPU.
This is the slow part of ingestion.

```
collection: docpilot_v1_c0  strategy: fixed 800/100 characters  cleaned: False
includes: False  documents: 20  chunks: 441  stored points: 441
```
**The receipt.** It tells you exactly what was built. Check that **chunks == stored points**.
If they differ, some chunks failed to save. Check also that the settings match what you meant.

```
includes resolved: 29, missing: 1
  missing: docs\_src/...
```
(C4 run only.) "Includes" means FastAPI pages say "insert code file X here", and we paste
in the real file. **The 1 missing comes from your Word notes**, which *quote* an include
marker as an example, so the resolver tries to fetch a file that doesn't exist. That's
pending **fix A**: only resolve includes for FastAPI sources.

```
manifest: ...\collections\docpilot_v1_c0.json      time: 38.6 s
```
The **manifest** is the collection's label (D-040): strategy, size, cleaned, includes. The
eval reads it, so every result file records **how its cards were cut**. You never have to
remember it.

**End point of an ingest run:** 0 chunks over the limit, chunks == stored points, no
document with 0 chunks, settings as intended. If all four hold, the box of cards is good
and you can sit the exam.

---

## 7. Reading the eval table, column by column

```
C0-v1 on dev  (474161b)
                 n  recall@1  recall@3  recall@5  strict_recall@5   mrr  ndcg@5
OVERALL         41     0.537     0.756      0.78            0.752  0.65   0.659
```

**The header:** config name, split, and **git commit**. The commit is how we prove which
code made the number. If it ever says `+dirty`, the code had uncommitted changes and the
row can't be trusted.

### The rows: three zoom levels

| Row | Meaning | Use it for |
|---|---|---|
| `OVERALL` | all 41 answerable dev questions | the headline number |
| `[docs]`, `[learning]`, `[interview]` | per **domain** (where the answer lives) | "which part of the library is weak?" |
| `factual`, `how-to`, `table-or-code` ... | per **question type** | "which kind of question is weak?" |

**Look at `n` before you trust a row.** `multi-hop` has n=1: one question flipping makes it
jump from 0.0 to 1.0. **Rows with n below about 5 are anecdotes, not evidence.** Read them
as a list of questions to open by hand, not as a score.

### The columns (all are averages over the questions in that row, from 0 to 1)

Example 0/1 list for one question: `[0, 1, 0, 0, 0, ...]`, so the right card came 2nd.

| Column | Question it answers | For the example |
|---|---|---|
| **recall@1** | Was the right card **first**? | 0 |
| **recall@3** | Was it in the **top 3**? | 1 |
| **recall@5** | Was it in the **top 5**? | 1 |
| **strict_recall@5** | If the question needs **several** cards, what **share** of them is in the top 5? | 1 (needs 1, found 1) |
| **mrr** | 1 / rank of the first right card: 1st → 1.0, 2nd → 0.5, 3rd → 0.33, missed → 0 | 0.5 |
| **ndcg@5** | Like MRR, but gives credit for **every** right card in the top 5, more for higher ranks | 0.63 |

**What each one is good for:**

- **recall@5** is the **headline**. Does the answer reach the LLM at all? We send the top 4
  chunks to the LLM, so @5 is a close, slightly generous proxy.
- **recall@1 and MRR** measure **ranking quality**. They matter because the LLM pays more
  attention to the first chunks, and because Phase 3's reranker exists exactly to push the
  right card to rank 1.
- **strict_recall@5** matters for multi-hop and comparison questions that need 2 cards.
  If it's lower than recall@5, we're finding **one** of the two cards but not both.
- **nDCG@5** is a single "how good is the whole top 5 order" number. Interviewers love it.

**How to translate a number into people-words:** recall@5 = 0.78 with n=41 means
**32 of 41 questions** had the right card in the top 5, and **9 did not**.
(0.78 × 41 = 32.)

---

## 8. Latency: what the numbers mean and how to judge them

```
search latency (warm, n=41): p50 2.2 ms, p95 3.2 ms
```

- **search latency** times **only step 8** (the Qdrant search). It doesn't include the
  LLM, and it doesn't include embedding the question.
- **warm:** the model was already loaded. The very first call is slower (cold) and is
  left out on purpose.
- **p50 = 2.2 ms:** half the questions were faster than this. This is the "typical" time.
- **p95 = 3.2 ms:** 95% were faster than this. This is the "bad day" time, and users
  remember bad days. With n=41, p95 is the 39th-fastest of 41, so it's nearly the slowest.

**How to judge latency: compare it with the whole answer time.**

| Stage | Typical time (real numbers) |
|---|---|
| vector search (today) | ~2 to 3 ms |
| whole answer, C4-200 on v0 (`1de3d22`, n=22) | p50 978 ms, p95 1230 ms |

Search is **under 1%** of the answer time. The LLM call is almost all of it. So **2.2 ms vs
3.1 ms (C0 vs C4) is meaningless for users**. It isn't the place to optimise. Search
latency only becomes a deciding factor in Phase 3, when a **reranker** adds a second model
(likely tens or hundreds of ms on CPU; unknown until we measure it).

**What does matter from chunking: tokens sent to the LLM.** C4-200 sent a p50 of **575
tokens** of context vs **1011** for C4-400 (v0 numbers). Fewer tokens means a faster, cheaper
LLM call and fewer Groq 429 "slow down" errors, with the same recall. That's why C4-200
was the provisional leader (D-042).

**The rule for latency:** always report **p50 and p95, warm, with n and the hardware**
(see `primer_latency.md`). "It's fast" isn't a number.

---

## 9. Today's story: what your two runs actually say

| (dev, golden v1, n=41, `474161b`) | R@1 | R@3 | R@5 | strict R@5 | MRR | nDCG@5 |
|---|---|---|---|---|---|---|
| C0-v1 (naive) | 0.537 | **0.756** | **0.780** | **0.752** | 0.650 | 0.659 |
| C4-200-v1 (hierarchical 200) | **0.585** | 0.732 | 0.756 | 0.728 | **0.669** | 0.659 |

**Step 1: convert to questions.** 1 question = 1/41 = **0.024**.

- R@5: 0.780 vs 0.756 → C0 has **1 more question** in the top 5 (32 vs 31).
- R@1: 0.537 vs 0.585 → C4 puts the right card **first** in **2 more** questions (22 vs 24).

**Step 2: is the gap bigger than the noise?** No. One or two questions out of 41 is a
coin-flip difference. **Overall: a tie.** C4 ranks a bit better, C0 reaches a bit more.

**Step 3: look under the tie (per question).** The totals hide real movement:

- C4 **fixed** 2 questions C0 missed: q-015 "Which class must my request data model
  inherit from?" and q-017 "Is it okay to put a JSON payload in a GET call?". It also moved
  many answers up to rank 1 (q-001, q-006, q-010, q-011, q-039).
- C4 **lost** 3 questions C0 found: q-045 (Pydantic strict mode how-to), q-047
  (`AliasChoices`), q-049 (keep a container's data). In all three C4's top 6 is **all from the
  right document** but **the wrong piece of it**. Right shelf, wrong page: with 200-token
  cards, the sentence with the answer sits in a small card that scores lower than its
  neighbours. That's why `how-to` fell from 0.8 to 0.4 (n=5, so 2 questions).
- 7 questions are missed by **both**: 4 of them are `table-or-code` (q-018, q-038, q-041,
  q-043). That's the weakest type in both runs (R@5 0.5). Pending **fixes B and C** target
  exactly this: Docling pads table lines with hundreds of dashes, and table captions get
  separated from their tables.

**Step 4: what's the conclusion of this run?**

1. Golden v1 **works** and gives us a new baseline: **C0-v1 R@5 0.780**. Every Phase 2
   and 3 row on v1 is measured against this.
2. C4-200 **isn't clearly better** than C0 on v1. The provisional leader from v0 is still
   provisional. We don't change the app yet.
3. The weak spots are **tables/code** (both configs) and **small-card how-to misses**
   (C4-200). These are concrete things to fix, not vague "make it better".
4. The PDF being half the library is **not** hurting other domains (3 or 0 of 165 slots).
5. Search latency is irrelevant at this size (~3 ms).

**That's the shape of every conclusion:** what the number is, whether the difference is
real, where it comes from (per question), and what we'll do next.

---

## 10. The end point of every run: 6 questions to ask

After **any** eval run, before you look at anything else, answer these:

1. **What exactly did I run?** Config, split, commit (not `+dirty`), golden version.
2. **What's the headline?** Overall R@5 and MRR, converted to "X of n questions".
3. **Compared to what?** Always the row above in `ABLATION.md` **on the same golden
   version**.
4. **Is the difference real?** Count questions. 1 or 2 out of 41 is noise. Look for a gap
   of **about 3 or more questions** (about 0.07), or a consistent pattern across
   domains/types.
5. **Where does it come from?** Open the per-question results (`per_question` in the JSON
   in `evals/results/`) for the questions that changed. Read the retrieved chunks.
6. **What's the decision?** Keep, drop, or "fix X and re-run". **Write it down** in
   `ABLATION.md` and `progress.md` with the commit.

If you can answer all six, the run is **finished**. If you can't answer 4 or 5, the run
gave you a number but not knowledge.

---

## 11. How we pick a winner (the decision rule)

The chunking winner is chosen in step 2.9 with **this order of tie-breakers**:

1. **Primary: recall@5** on dev (does the answer reach the LLM?).
2. If within noise (≤ 2 questions): **MRR / recall@1** (is it ranked first?).
3. If still close: **tokens sent to the LLM** (fewer = faster and cheaper).
4. Then **ingest cost** (C5 contextual costs 1 LLM call per chunk; C2 semantic needs extra
   embedding work).
5. Then **simplicity**: simpler wins a tie, because it's easier to debug and explain.

Then, **once**, run the **test split** for the winner and C0. If the winner also beats C0 on
test, it's real. Record it as a decision (D-0xx) with the numbers, and switch the app to it.
If it doesn't beat C0 on test, say so honestly: that's a valid result too.

**Never** pick a winner from one row with n=1, from a `+dirty` run, or by mixing golden
versions.

---

## 12. Where we are, what comes next

```
Phase 2:  2.1-2.5 data quality ✔   2.6 chunkers ✔   2.7 PDF/Word ✔   2.8 corpus+golden v1 ✔
          v1 baselines (today) ✔
          fixes A/B/C  ->  2.9 full chunking matrix on v1 + pick winner + test once
          ->  2.10 CI eval gate  ->  Phase 2 gate (your interview notes, PR, tag phase-2)
Phase 3:  hybrid search, reranker, query transforms   (only after the gate)
```

---

## 13. Self-check (answer without looking)

1. In the pipeline, which comes first, chunking or retrieval? Why does that order matter
   for tuning?
2. Why is `n` 41 when dev has 46 questions?
3. C0 scored R@5 0.842 on v0 and 0.780 on v1. Did C0 get worse? Explain.
4. Recall@5 = 0.756 with n=41: how many questions is that?
5. The right card came 4th. What are recall@3, recall@5 and the reciprocal rank?
6. Why is C0-v1 vs C4-200-v1 not a pure chunking comparison?
7. Search p50 is 2.2 ms. Why don't we care about 2.2 vs 3.1 ms right now?
8. Name the 6 questions you ask after every run.
9. Why do we run the test split only once?

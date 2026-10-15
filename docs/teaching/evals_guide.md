# Evals: The Complete Guide (Part 1 of 2: Concepts)

Your study guide for evals, written from everything we did in DocPilot Phase 1 (sessions of
2026-10-12 to 2026-10-14). Simple words first, then the precise version.
Part 2 ([2_evals_guide.md](2_evals_guide.md)) has the interview questions with answers.

**Number rule:** every DocPilot number here comes from a real run (file named next to it).
Numbers marked *toy example* are made up only to show how a formula works.

---

## Contents

1. What an eval is
2. Do real companies do this?
3. The eval loop
4. The two jobs of a RAG system
5. Step 1: error analysis (look before you measure)
6. Step 2: the golden dataset (the answer key)
7. Step 3: is this chunk a hit? (matching)
8. Retrieval metrics: Recall@k, MRR, nDCG
9. Reading a results table
10. Abstention: saying "I don't know" at the right time
11. Generation evals and LLM-as-a-judge (coming in Phase 3.9)
12. Latency: how fast, measured properly
13. The ablation table: one change at a time
14. Making numbers trustworthy (reproducibility)
15. Evals in CI and after deployment
16. Common mistakes
17. Glossary

---

## 1. What an eval is

**Simple:** an eval is an **exam for your AI system**. Like a driving test:

| Driving test | AI eval | In DocPilot |
|---|---|---|
| a fixed route | a fixed list of questions | 32 golden questions |
| the examiner's checklist | the answer key | page + exact sentence that holds the answer |
| the examiner | code, or another AI acting as judge | `evals/matching.py`, later an LLM judge |
| the score | numbers | Recall@5 = 0.842 |

**Precise:** an eval is a **repeatable measurement** of a system's quality on a **fixed
dataset**, with a **fixed scoring rule**, so that two versions of the system can be
compared fairly.

**Why it matters:** without evals, "my chatbot got better" is a feeling. With evals it is
proof: "Recall@5 went from A to B on the same 19 questions".

---

## 2. Do real companies do this?

Yes. It is one of the most asked-for AI engineering skills.

- **AI labs** (OpenAI, Anthropic, Google): large teams build evals before every model release.
- **Companies with AI products** (support bots, search, coding assistants): good teams keep
  a golden set like ours and run it before every change. Often called
  **eval-driven development**: write the test first, then improve until the number moves.
- **Many smaller teams** test by "asking a few questions; looked fine". That is exactly why
  someone who can build and explain evals stands out.

Saying: **"You can't improve what you don't measure."**

---

## 3. The eval loop

```text
1. LOOK at failures by hand        -> step 1b (10 questions, failure log)
2. WRITE an answer key             -> step 1c (32 golden questions)
3. SCORE automatically             -> step 1d (C0 score, L0 speed, abstention)
4. CHANGE one thing                -> Phase 2 (better chunking), Phase 3 (hybrid, reranker)
5. SCORE again, compare            -> the ablation table
6. ADD new real failures to the key -> so a fixed bug cannot come back silently
```

Step 1 is the one most people skip, and it is the most important: you cannot write a good
exam if you do not know where the students fail.

---

## 4. The two jobs of a RAG system

```text
question -> [JOB 1: FIND the right chunks] -> [JOB 2: WRITE the answer from them] -> answer
                     retrieval eval                       generation eval
```

Analogy: an open-book exam. Job 1 = did the student open the book at the right page?
Job 2 = did they write a correct answer **from that page**, without making things up?

**Why test them separately?** Because the cure is different. Real example from DocPilot:

| Question | Job 1 (retrieval) | Job 2 (answer) | Real cause |
|---|---|---|---|
| q-007 "Show me the code for a minimal FastAPI app" | right chunk at **rank 1** | "not found" | the chunk holds `{* ...py *}`, a pointer to code we never downloaded |

If you only scored the final answer, you would blame the search and waste a week. The split
tells you the fix belongs in **ingestion** (Phase 2.3, include resolver).

Rule: **check retrieval first.** If the right page never arrives, the writer cannot succeed.
Retrieval evals are also free (no LLM), so they can run on every change.

---

## 5. Step 1: error analysis (look before you measure)

**What:** ask a handful of questions by hand, read the retrieved chunks and the answer, and
write down *why* each one failed. File: `docs/failure_log_phase1.md` (10 questions).

**What we found (real, 2026-10-12, 51 chunks from 4 FastAPI pages):**
- Retrieval was mostly fine; the **content of the chunks** was the problem: include markers
  instead of code, sentences cut in the middle, HTML noise.
- **Q1 was the most dangerous failure:** correct rule ("default `None`") but the LLM
  **invented code** and wrote "Example (from the docs)". It looked perfect. This is an
  **ungrounded** answer (a hallucination).
- **Scores cannot separate good from bad chunks:** an off-topic chunk for a PostgreSQL
  question scored 0.705; the correct chunk for another question scored 0.700. So
  "throw away chunks below score X" does not work.

**Why it matters:** a number says *how often* things fail; reading says *why*. The "why"
decides what to build next.

---

## 6. Step 2: the golden dataset (the answer key)

Files: `evals/golden/dev.jsonl` (22 items), `evals/golden/test.jsonl` (10 items).

**One item (shown on several lines; in the file it is one line = JSONL):**
```json
{"id": "q-001", "question": "How do I make a query parameter optional?", "type": "how-to",
 "should_answer": true, "reference_answer": "Give it a default value of None; ...",
 "evidence": [{"doc": "fastapi/query-params.md",
               "snippet": "you can declare optional query parameters, by setting their default to `None`"}],
 "difficulty": "easy", "split": "dev", "notes": "..."}
```

| Field | Plain meaning |
|---|---|
| `question` | what a user would ask |
| `type` | kind of question, so you can see *where* the system is weak |
| `should_answer` | `false` = trick question, the docs do not say; correct behaviour is "not found" |
| `reference_answer` | the teacher's model answer (used by the judge in Phase 3.9) |
| `evidence` | which page, and one **exact** sentence copied from it |

### 6.1 Why an exact sentence, not a chunk number?
Chunk numbers change every time chunking changes (Phase 2 tries six strategies). Chunk 7
in one strategy is different text in another. The **page text never changes**, so one
answer key scores every strategy. (Decision D-010.)

### 6.2 Dev and test
- **dev** (22): practise on it as often as you like.
- **test** (10): the final exam, opened **only at phase gates**.

If you tune settings while looking at test scores, test becomes a second practice set and
the score stops being honest. That is called **overfitting to the test set**.
Our 10 failure-log questions are all in dev: we had already seen their answers.

### 6.3 Unanswerable questions (16%)
5 of 32 have no answer in the pages. Most are **near-misses**: the pages look related, so
the search returns convincing chunks. Examples: "What status code on validation failure?"
(the number 422 is on none of the 4 pages), JWT, `max_length`. They test whether the
system refuses instead of guessing.

### 6.4 Question types (8)
factual, how-to, exact-identifier, paraphrase, comparison, multi-hop, table-or-code,
not-in-docs. Not yet covered (no matching documents yet): version-specific,
concept, interview, adversarial, risky. They arrive in Phases 2.8 and 6.

### 6.5 The validator
`python evals/validate_golden.py` checks: valid JSON, all fields, unique ids, sensible
`should_answer`/`evidence`, and that **every snippet appears character for character in
its page**. Why so strict? One typo silently turns a correct hit into a miss and lowers the
score, and nobody notices. Seven tests prove the checker catches these mistakes.

### 6.6 How big should it be?
Ours is small on purpose (32). Small sets are quick to build and read, but noisy:
**with 19 scored questions, one question moves Recall by about 5 points** (1/19 = 0.053).
Bigger sets give steadier numbers; Phase 2.8 adds at least 10 questions per domain.

---

## 7. Step 3: is this chunk a hit? (matching)

File: `evals/matching.py`. For each retrieved chunk we ask: does it contain the golden
sentence? Answer 1 (yes) or 0 (no).

Rules, each with its reason:
1. **Normalise** both texts (lowercase, squash spaces and line breaks), so formatting
   differences do not cause misses.
2. **Same page only:** a chunk from another page cannot count, even with similar words.
3. **70% overlap is enough** (`min_overlap = 0.7`): a sentence cut in half by a chunk
   boundary still counts if most of it is in one chunk. The value is saved with every result.
4. **Count each golden sentence once:** chunks overlap by 100 characters, so two neighbours
   can contain the same sentence; counting both would inflate the score.

The output for one question is a **relevance list** in rank order, e.g. `[0, 1, 0, 0, 0]`
= "the 2nd chunk was the right one".

---

## 8. Retrieval metrics: Recall@k, MRR, nDCG

All three start from the relevance list. We fetch **10 chunks** per question so one search
gives @1, @3 and @5. (DocPilot itself still sends only the top **4** to the LLM.)

### 8.1 Recall@k: "is the right chunk anywhere in the top k?"
Per question: 1 if there is a 1 in the first k positions, else 0. Then average.

Real DocPilot rows:
| id | relevance | Recall@1 | Recall@5 |
|---|---|---|---|
| q-005 | `[1, 0, 0, ...]` | 1 | 1 |
| q-001 | `[0, 1, 0, ...]` | 0 | 1 |
| q-023 | `[0, 0, 0, ...]` (all zeros) | 0 | 0 |

**Trick: turn the average back into a count.** Recall is an average of 0s and 1s, so
`score x n = number found`. C0 Recall@5 0.842 x 19 = **16 found**, 3 missed.
Recall@1 0.526 x 19 = **10 at rank 1**. (This does not work for MRR: its scores are fractions.)

**Strict Recall@k:** for questions with several golden sentences, the *share* found.
q-010 needs 2 sentences (two pages); finding 1 gives 0.5.

### 8.2 MRR (Mean Reciprocal Rank): "how high was the first right chunk?"
Per question: **1 / rank** of the first 1 (0 if none). Rank 1 = 1.0, rank 2 = 0.5,
rank 3 = 0.33, rank 6 = 0.167. Then average over questions.
Like a race: 1st place gets a full medal, 3rd a third of one.
Real: q-001 = 0.5, q-005 = 1.0. C0 MRR = **0.667**.

### 8.3 nDCG@k: "are all the good chunks near the top?"
Each relevant chunk earns `1 / log2(rank + 1)` points: rank 1 = 1.0, rank 2 = 0.63,
rank 3 = 0.5, rank 4 = 0.43, rank 5 = 0.39. Divide by the best possible score (all golden
sentences at the top). 1.0 = perfect order. It matters most when a question has several
golden sentences. *Toy example:* one sentence, found at rank 2: 0.63 / 1.0 = 0.63.

### 8.4 Why three numbers?
| Metric | Question it answers |
|---|---|
| Recall@k | found it at all? |
| MRR | found it **first**? |
| nDCG | are **all** the useful ones at the top? |

A change can raise one and lower another. A **reranker** (Phase 3) mostly raises Recall@1
and MRR, because it re-sorts what was already found.

---

## 9. Reading a results table

Real C0 output (2026-10-14, commit `06891f1`, dev, n=19,
`evals/results/2026-10-14_C0_dev_retrieval.json`):

| Metric | C0 |
|---|---|
| Recall@1 | 0.526 |
| Recall@3 | 0.842 |
| **Recall@5** | **0.842** |
| strict Recall@5 | 0.781 |
| **MRR** | **0.667** |
| **nDCG@5** | **0.670** |
| search latency (warm) | p50 1.3 ms, p95 2.2 ms |

**How to read it in plain words:** "The search finds the right chunk for 16 of 19 questions,
but puts it first only for 10. Finding is OK; ordering is weak."

**The 3 misses, and the pattern:**
| id | What happened | Why |
|---|---|---|
| q-017 "JSON **payload** in a GET **call**?" | rank 6 | page says "body" and "request": different words, same meaning |
| q-018 "What does FastAPI do with the body?" | rank 6 | the answer is a bullet list, spread across chunks |
| q-023 "fixed set of **allowed** values" | not in top 10 | page says "**predefined** values"; another Enum chunk looked closer |

All three are **word-mismatch** problems: the classic weakness of dense-only search. Fixes
to test later: query rewriting, hybrid search (Phase 3), a reranker.

**Per-type rows:** they have n = 1 to 5 questions each. "multi-hop 0.0 at @1" is one single
question. Use small rows as **clues to read**, never as scores to compare.

**How to find failures yourself:** open the result JSON, Ctrl+F `"recall@5": 0.0`.

---

## 10. Abstention: saying "I don't know" at the right time

**What:** does DocPilot reply with the exact sentence `I could not find this in the
documents.` exactly when it should? Checked with plain code (`phrase in answer`): free to
mark, exact and repeatable. File: `evals/run_abstention_check.py`.

**Two different ways to be wrong:**
| Error | Meaning | Risk |
|---|---|---|
| **false answer** | should refuse, but answered | user gets a made-up answer (dangerous) |
| **false refusal** | should answer, but refused | user gets nothing (annoying, but safe) |

**Real C0 (2026-10-14, commit `b061d62`, dev n=22,
`evals/results/2026-10-14_C0_dev_abstention.json`):**
- accuracy **0.909** (20 of 22)
- false answers **0 of 3** (all three trick questions refused correctly)
- false refusals **2 of 19**: q-007 (code is only an include marker) and q-017 (right chunk
  was rank 6, but the LLM only sees the top 4)

**Lesson:** both false refusals were caused **upstream** (ingestion, retrieval), not by the
LLM. The LLM behaved honestly with what it was given. Evals let you prove that.

---

## 11. Generation evals and LLM-as-a-judge (coming in Phase 3.9)

For a written answer there is no simple yes/no, so a second LLM acts as the **judge**.

| Metric | Simple question | DocPilot example |
|---|---|---|
| **Faithfulness** (groundedness) | did it say only what the chunks say? | 1b Q1 failed: invented code "from the docs" |
| **Answer relevancy** | did it answer what was asked? | 1b Q10: "yes, use an Enum" but not *how* |
| **Correctness** | does it match the reference answer? | 1b Q1's rule was correct |
| **Abstention** | refuse exactly when it should | section 10 |

**How a faithfulness judge marks (two steps, more reliable than one big score):**
```text
Answer: "Use default None [1]. Code: def read_items(q: str | None = None)"
1) list the claims:   (a) default None makes it optional   (b) this code is in the docs
2) check each claim against the chunks:   (a) supported   (b) NOT supported
Faithfulness = 1 / 2 = 0.5          (toy example)
```

**Judges have habits (biases), so:**
- they prefer **longer** answers -> judge with clear rules, not "is this good?";
- they prefer answers in **their own style** -> use a different model as judge;
- small free models are **inconsistent** -> temperature 0, and check about 20% by hand
  and report the agreement rate;
- always write down **which judge model** produced a number.

Tools that package this: **RAGAS**, **DeepEval** (Phase 4.5). Our rule is "raw first":
build the judge by hand, then compare with the library, so you know what it does inside.

---

## 12. Latency: how fast, measured properly

**Latency = how long the user waits.** Measure **each stage**, not just the total:
```text
question -> embed_query -> search -> llm -> answer
```

| Word | Simple meaning |
|---|---|
| **p50** (median) | half the requests are faster: the typical user |
| **p95** | 95% are faster: the unlucky user; alerts watch this |
| **cold** | first request, loads the model (about 2,000 ms in step 1b) |
| **warm** | every request after that: what users of a running service get |
| **429** | "too many requests": the free provider told us to wait |
| **TTFT** | time to first token: how fast the first word appears (Phase 7, streaming) |

**Why not the average?** *Toy example:* 9 requests take 1 s and 1 takes 30 s. The average is
3.9 s, a wait nobody had. p50 = 1 s shows the typical case; p95/max shows the slow tail.

**Nearest-rank percentile:** sort the times and pick a real one (p95 of 22 values = the
21st). The result is always a time some request really took.

**Real L0 (2026-10-14, commit `8295859`, warm after 1 warm-up, n=22, laptop CPU,
Groq `openai/gpt-oss-120b`, `evals/results/2026-10-14_C0_dev_latency.json`):**
| Stage | p50 | p95 |
|---|---|---|
| embed_query | 15.8 ms | 85.4 ms |
| search | 1.0 ms | 1.9 ms |
| llm | 1060.4 ms | 1748.8 ms |
| **total** | **1107.2 ms** | **1763.7 ms** |
| wall incl. 429 waits | 5933.9 ms | 8208.5 ms |

**Lessons:**
1. **Optimise the biggest part first.** The LLM is about 96% of the time; a 10x faster
   search would save under 1 ms.
2. **Warm vs cold is huge:** embedding about 2,000 ms cold vs 16 ms warm. That is why the
   API (step 1e) loads everything once at startup.
3. **The provider's rate limit was the biggest risk:** 15 retries; with waits, p50 rose to
   about 5.9 s.

**Is our latency "good"?** There is no universal best number. Companies (1) measure a
baseline first, (2) set a **budget** from what users need, written as an **SLO** like
"p95 total under X s", (3) make every new feature "pay" from that budget. A common UX rule
of thumb (Jakob Nielsen): about 0.1 s feels instant, about 1 s keeps the user's flow,
about 10 s loses attention. Our budget X is set after L0, by you, not guessed.

---

## 13. The ablation table: one change at a time

File: `evals/ABLATION.md`. **Ablation** = change **one** thing, run the **same** eval,
compare. One row per configuration (C0 = naive baseline, C1 = recursive chunking, ...).

Real C0 row: Recall@5 0.842, MRR 0.667, nDCG@5 0.670, abstention 0.909,
p50 total 1107 ms, p95 total 1764 ms, 1 LLM call per question.

Rules:
1. **One change per row.** Change chunking and the model together, and you cannot tell
   which helped.
2. **Same golden set version** for every row being compared.
3. **Record the cost next to the gain** (latency, LLM calls): "the reranker raised MRR by A
   and cost B ms at p95" is a decision; "MRR went up" is not.
4. **Small differences are ties.** With 19 questions, 1 question = about 5 points.

---

## 14. Making numbers trustworthy (reproducibility)

Every result file in `evals/results/` stores how it was made:
| Label | Why |
|---|---|
| `git_commit` (with `+dirty` if uncommitted) | the exact code; commit first, then run |
| `date`, `config_id`, `split` | which run and which questions |
| `settings` (chunk size, overlap, model + revision, top_k, min_overlap, LLM model) | what to change back to repeat it |
| `per_question` | read failures later without re-running |

Other habits: corpus pinned to one commit (D-029), embedding model pinned to a revision,
`temperature=0` for the LLM, validator before every run, test split only at gates.

---

## 15. Evals in CI and after deployment

**CI (continuous integration):** GitHub runs checks on every pull request (step 1f: lint,
tests, file length). In Phase 2.10 a **retrieval eval gate** joins: if Recall@5 or MRR
drops below the baseline minus a small tolerance, the PR turns red and cannot merge. Only
retrieval evals go there: free and the same result every time. LLM-based evals cost tokens
and vary, so they run by hand or nightly.

**Online monitoring (Phase 7):** after release there is no answer key. You watch signals on
real traffic: rising "not found" rate, slow p95, thumbs-down clicks, new kinds of
questions. Real failures are copied into the golden set (a **regression test**).

| | Offline eval | Online monitoring |
|---|---|---|
| When | before release | after release |
| Answer key | yes | no |
| Like | the driving test | watching the driver on real roads |

---

## 16. Common mistakes

1. Measuring only the final answer (cannot tell retrieval failures from writing failures).
2. Tuning on the test set.
3. Changing two things at once.
4. Reading 0.84 vs 0.86 as "better" on 19 questions.
5. Looking only at the average, never at the failing questions.
6. Trusting an LLM judge without checking a sample by hand.
7. Reporting an average latency instead of p50/p95, or mixing cold and warm runs.
8. Numbers without labels (no commit, no settings, no n): nobody can repeat them.
9. A golden set copied from the page wording only: paraphrase failures stay hidden.
10. Predicting nothing before a run: you learn nothing from the result.

---

## 17. Glossary

| Term | One-line meaning |
|---|---|
| eval | a repeatable exam for an AI system |
| golden set / answer key | questions + where the correct answer is |
| dev / test split | practice set / final-exam set |
| relevance list | 0/1 per retrieved chunk, in rank order |
| Recall@k | share of questions with a right chunk in the top k |
| MRR | average of 1/rank of the first right chunk |
| nDCG@k | how well the right chunks are ordered at the top (1.0 = perfect) |
| abstention | answering "not found" when the docs do not say |
| false answer / false refusal | answered when it should refuse / refused when it should answer |
| faithfulness | everything said is supported by the retrieved chunks |
| hallucination | content not supported by the sources |
| LLM-as-a-judge | a second LLM marks answers using rules |
| p50 / p95 | median / slow-tail time |
| cold / warm | first call (loads things) / later calls |
| SLO | a target like "p95 under X s" |
| ablation | change one thing, compare on the same eval |
| regression test | an old failure kept in the test set so it cannot return |
| overfitting to test | tuning until the test looks good; the score stops being honest |

Continue with the interview questions: [2_evals_guide.md](2_evals_guide.md).

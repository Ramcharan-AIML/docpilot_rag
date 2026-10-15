# Primer: Evals From Zero (explained like you are a child, then like an engineer)

You said you know nothing about evals. Good: start here, before Phase 1 step 1c.
Every number in this file is an **arithmetic example of a formula**, not a result of our
system. Our real numbers only ever come from real runs.

---

## 1. The story: the spelling test

A teacher wants to know if a new way of teaching spelling works.

- Bad way: "The children *seem* better." (That is a feeling, not proof.)
- Good way: give the **same spelling test** before and after, mark it with the **same answer
  key**, and compare the **scores**.

An **eval** (evaluation) is exactly that spelling test, for an AI system.

| Spelling test | DocPilot |
|---|---|
| The test questions | Questions a developer might ask |
| The answer key | For each question: the correct answer and *where in the docs* it is |
| Marking | Code (or a "judge" AI) that checks each answer |
| The score | Numbers like Recall@5 or faithfulness |
| Before and after | C0 (naive baseline) vs C1, C2, ... (each improvement) |

**Why this matters for your job hunt:** almost anyone can build a chatbot in an afternoon.
Very few people can say *"hybrid search moved Recall@5 from A to B on my 60-question test
set"*. That sentence is what makes an interviewer take your project seriously.

---

## 2. Two separate questions we test

A RAG system does two jobs, so we test two things:

```text
question ──▶ [1. FIND the right doc pieces] ──▶ [2. WRITE the answer from them] ──▶ answer
                     │                                      │
             retrieval evals                         generation evals
       "did we fetch the right page?"        "is the answer true, on-topic, cited?"
```

If job 1 fails, job 2 cannot succeed: the writer never saw the right page. So we always check
retrieval first. It is also free (no AI judge needed), so we can run it on every change.

---

## 3. The answer key (golden dataset)

One line per question (file `evals/golden/dev.jsonl`):

```json
{"id": "q-001", "question": "How do I make a query parameter optional?",
 "type": "how-to", "should_answer": true,
 "reference_answer": "Give it a default value of None.",
 "evidence": [{"doc": "fastapi/query-params.md", "snippet": "a short sentence copied from the doc"}]}
```

| Field | Child explanation |
|---|---|
| `question` | what the child is asked |
| `type` | which kind of question (how-to, exact name, paraphrase, ...) so we can see *where* we are weak |
| `should_answer` | `false` means "this is a trick question, the book does not say": the right move is to say "I could not find this" |
| `reference_answer` | the teacher's model answer |
| `evidence` | which page and which exact sentence holds the answer |

**Why a sentence (snippet) and not a chunk number?** Later we cut the docs in six different
ways (Phase 2). Chunk number 7 in one cutting is a different piece of text in another. A
sentence copied from the doc stays the same no matter how we cut. One answer key works for
every experiment.

**Two piles: dev and test.** You practise on the **dev** pile every day. The **test** pile
stays in a drawer and is opened only at phase gates. Why: if you keep tuning until the test
looks good, you have learned the test, not the skill. (This is called **overfitting**.)

---

## 4. Retrieval metrics, worked by hand

Our system returns a ranked list of chunks for each question. For each chunk we ask: "does it
contain the gold sentence?" 1 = yes, 0 = no.

**Toy example: three questions, top 5 chunks each**

```text
Q1: [1, 0, 0, 0, 0]   correct chunk at rank 1
Q2: [0, 0, 1, 0, 0]   correct chunk at rank 3
Q3: [0, 0, 0, 0, 0]   correct chunk not found at all
```

### Recall@k ("is it anywhere in the top k?")

Like asking: "did the right book end up somewhere on the table?"

| | @1 | @3 | @5 |
|---|---|---|---|
| Q1 | 1 | 1 | 1 |
| Q2 | 0 | 1 | 1 |
| Q3 | 0 | 0 | 0 |
| **Average** | **0.33** | **0.67** | **0.67** |

### MRR ("how high up was the first right one?")

Score each question `1 / rank of the first correct chunk` (0 if none):
Q1 = 1/1 = 1.0, Q2 = 1/3 = 0.33, Q3 = 0. **MRR = (1.0 + 0.33 + 0) / 3 = 0.44.**
Like a race: first place gets a full medal, third place gets a third of one.

### nDCG@5 ("are all the good ones near the top?")

Each correct chunk earns `1 / log2(rank + 1)` points: rank 1 -> 1.0, rank 2 -> 0.63,
rank 3 -> 0.5, rank 4 -> 0.43, rank 5 -> 0.39. Then divide by the best possible score.
For Q2: earned 0.5, best possible (correct chunk at rank 1) = 1.0, so nDCG = 0.5.
It matters most when a question has several correct chunks.

**Why three numbers?** Recall says "found it?", MRR says "found it first?", nDCG says "are
the useful ones at the top?". A change can raise one and lower another.

---

## 5. Generation metrics: grading the written answer

Here there is no simple yes/no. We need a **judge**: another LLM, given clear marking rules.

| Metric | Child question | Example of failing |
|---|---|---|
| **Faithfulness** | "Did you only say things the book says?" | Answer invents a default value no chunk mentions |
| **Answer relevancy** | "Did you answer what was asked?" | Correct facts about path params when asked about query params |
| **Correctness** | "Does it match the teacher's answer?" | Says `None` makes it *required* |
| **Abstention accuracy** | "Did you say 'I don't know' exactly when you should?" | Makes up an answer to a trick question |

**How the faithfulness judge marks (two steps, more reliable than one big score):**

```text
Answer: "Set a default of None [1]. It is then validated as a string [2]."
Step 1, list claims:  (a) default None makes it optional   (b) it is validated as a string
Step 2, check each against the chunks:  (a) supported   (b) not in any chunk
Faithfulness = 1 supported / 2 claims = 0.5
```

**Can we trust the judge?** Not blindly. Judges have habits:
- they like **long** answers more,
- they like answers written **in their own style** (so we use a different model to judge),
- small free models are **inconsistent**.

So we: use temperature 0, check about 20% of items **by hand**, report how often we agreed
with the judge, and always write down **which judge model** gave the number.

**Abstention is special:** we check it with plain code. The system must use the exact phrase
"I could not find this in the documents." so we can search for it. Free, exact, repeatable.

---

## 6. Other evals that appear later

| Layer | What it checks | Phase |
|---|---|---|
| Agent | did it pick the right route / tool / arguments? how many loops? | 4-5 |
| Guardrails | how many attacks got through? how many normal questions were wrongly blocked? | 6 |
| System | how fast (p50/p95 latency)? how often did it fail? | 3, 7 |
| Online monitoring | the same ideas measured on **real traffic** after deployment | 7 |

**Offline evals vs online monitoring:** offline = the exam in the classroom, with an answer
key, before release. Online = watching the student at their real job, with no answer key,
looking for warning signs (more "I don't know" answers than usual, new kinds of questions).
See `primer_rag_monitoring.md`.

---

## 7. The ablation table: the scoreboard of experiments

**Ablation** = change ONE thing, run the SAME test, compare.

| Config | What changed | Recall@5 | MRR |
|---|---|---|---|
| C0 | naive baseline | n/a | n/a |
| C1 | recursive chunking | n/a | n/a |
| ... | ... | ... | ... |

Rules: one change per row; same answer key version for every row; record cost too (time,
LLM calls); a tiny difference is a **tie** (with 30 questions, one question = 3.3 points).
This table, filled with real numbers, is the heart of your README and your interviews.

**MLflow** (from Phase 2) records every run's settings and scores automatically, and
`evals/ABLATION.md` is generated from those records. See `primer_mlflow.md`.

---

## 8. Evals as a safety net: the CI gate

Every pull request runs the retrieval eval on a small fixed set of documents. If Recall@5 or
MRR drops below `baseline - tolerance`, the PR turns red and cannot merge (branch protection).
It is like a spelling test the robot gives before any change enters the printed book. Only
retrieval evals are used here: they are free and give the same answer every time.

---

## 9. Where you build each piece

| Piece | File | Step |
|---|---|---|
| Answer key + checker | `evals/golden/*.jsonl`, `evals/validate_golden.py` | 1c |
| Hit matching | `evals/matching.py` | 1d.1 |
| Recall, MRR, nDCG (by hand) | `evals/metrics.py` + tests | 1d.2 |
| Eval runner, C0 | `evals/run_retrieval_eval.py` | 1d.3 |
| Abstention check | `evals/run_abstention_check.py` | 1d.4 |
| MLflow logging, ablation table | `evals/tracking.py`, `evals/make_ablation.py` | 2.0, 2.9 |
| CI eval gate | `evals/check_gate.py`, `.github/workflows/ci.yml` | 2.10 |
| Judge metrics | `evals/run_generation_eval.py` | 3.9 |
| RAGAS / DeepEval comparison | `evals/run_ragas_eval.py` | 4.5 |
| Agent evals | `evals/run_agent_eval.py` | 5.7 |
| Red-team evals | `evals/run_redteam_eval.py` | 6.1 |
| Online RAG monitoring | `observability/rag_monitor.py` | 7 |

---

## 10. Common mistakes

1. Changing two things at once, then not knowing which one helped.
2. Comparing rows that used different answer-key versions.
3. Tuning on the test pile.
4. Trusting the judge without checking by hand.
5. Reading 0.70 vs 0.71 as "better".
6. Only looking at the average and never reading the failing questions.

---

## 11. Self-check (say the answers out loud)

1. Explain an eval using the spelling-test story.
2. Why test retrieval before generation?
3. Compute Recall@1, Recall@3, and reciprocal rank for `[0, 1, 0]`.
4. Why label evidence with a sentence, not a chunk number?
5. Faithful but irrelevant: give an example.
6. Three judge habits, and what we do about each.
7. Offline eval vs online monitoring: what is the difference?

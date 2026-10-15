Continues from [evals_guide.md](evals_guide.md)

# Evals: The Complete Guide (Part 2 of 2: Interview Questions)

How to practise: read the question, **say your answer out loud first**, then read the
model answer. The model answers are short on purpose: in an interview, say the short
version first and add detail only if asked.

**Your real numbers, ready to quote (Phase 1, C0, dev split):**
| What | Number | Source |
|---|---|---|
| Recall@1 / Recall@5 | 0.526 / 0.842 (10 and 16 of 19) | `2026-10-14_C0_dev_retrieval.json`, commit `06891f1` |
| MRR / nDCG@5 | 0.667 / 0.670 | same |
| Abstention | 0.909; 0/3 false answers; 2/19 false refusals | `..._abstention.json`, `b061d62` |
| Latency total (warm, n=22) | p50 1107 ms, p95 1764 ms; LLM about 96% | `..._latency.json`, `8295859` |
| Rate limits | 15 retries; p50 with waits 5.9 s | same |
| Golden set | 32 items: 22 dev, 10 test, 5 unanswerable, 8 types | `evals/golden/` |

---

## A. Direct questions (definitions and "why")

**A1. What is an eval?**
A repeatable exam for an AI system: a fixed set of questions, an answer key, and a fixed
scoring rule, so two versions can be compared fairly.

**A2. Why do evals matter for RAG?**
RAG has many settings (chunking, embedding model, top-k, prompts). Without a fixed
measurement you cannot tell if a change helped, hurt, or did nothing.

**A3. What is the difference between retrieval evals and generation evals?**
Retrieval: did we fetch the chunk that holds the answer (Recall, MRR, nDCG; plain code,
free). Generation: is the written answer faithful, relevant and correct (needs a judge,
costs tokens). Measuring both tells you *where* a failure happens.

**A4. What is a golden dataset?**
Questions with a known answer and the evidence location. Ours stores the page plus an exact
sentence, so it works for any chunking strategy.

**A5. Why label evidence with a sentence and not a chunk id?**
Chunk ids change whenever chunking changes; the document text does not. One answer key can
then score every strategy.

**A6. Why split into dev and test?**
Dev is for trying ideas; test is the final exam used only at gates. Tuning on test makes
its score optimistic (overfitting to the test set).

**A7. Define Recall@k.**
Share of questions where at least one correct chunk is in the top k results.

**A8. Define MRR.**
Mean of 1/rank of the first correct chunk (0 if none). It rewards putting the right chunk
first.

**A9. Define nDCG@k in one sentence.**
A score from 0 to 1 for how well all relevant chunks are ordered at the top, giving less
credit the lower they appear (discount 1/log2(rank+1)).

**A10. Recall@5 is high but MRR is low. What does it mean?**
The right chunk is usually found but not ranked first. A reranker is the classic fix.

**A11. What is strict recall?**
For questions needing several pieces of evidence: the share of those pieces found in the
top k, not just "any one".

**A12. What is abstention, and why measure it?**
Saying "not found" when the documents do not contain the answer. It measures honesty:
a confident wrong answer is worse than "I don't know".

**A13. False answer vs false refusal: which is worse?**
Usually a false answer (made-up content the user trusts). A false refusal is annoying but
safe. Report them separately; one accuracy number hides which one you have.

**A14. What is faithfulness?**
Every claim in the answer is supported by the retrieved context. Unsupported claims are
hallucinations, even if they happen to be true in the real world.

**A15. What is LLM-as-a-judge and what are its weaknesses?**
A second LLM marks answers using written rules. Weaknesses: prefers long answers, prefers
its own style, inconsistent on small models. Mitigate: clear rubric, temperature 0, a
different judge model, hand-check a sample and report agreement.

**A16. Why p95 latency and not the average?**
Averages hide the slow tail; p95 shows what the unlucky 5% wait. Alerts and SLOs use
percentiles.

**A17. Cold vs warm latency?**
Cold = first call, includes loading models and opening connections. Warm = steady state.
Measure them separately; mixing them makes both numbers wrong.

**A18. What is an ablation study?**
Change one component, keep everything else fixed, re-run the same eval, compare.

**A19. Offline eval vs online monitoring?**
Offline: before release, with an answer key. Online: after release, on real traffic,
without an answer key, watching signals (refusal rate, latency, feedback).

**A20. How do you know a difference is real and not noise?**
Know the step size: with n questions, one question = 1/n. On 19 questions that is about
5 points, so a 2-point change is a tie. Bigger sets or repeated runs give confidence.

**A21. What are RAGAS and DeepEval?**
Libraries that package RAG metrics (faithfulness, answer relevancy, context precision and
recall), mostly with LLM judges. Useful, but you should know what they compute inside;
that is why we wrote our metrics by hand first.

**A22. What is a regression test in evals?**
A past failure kept in the golden set, so that if it breaks again, the score shows it.

**A23. Why is temperature 0 used in evals?**
To make the LLM's output as repeatable as possible, so score changes come from your change,
not from randomness.

**A24. What should every eval result record?**
Code commit, date, dataset version and split, all settings, n, and per-question details.

---

## B. Scenario questions about DocPilot (say what you did and why)

**B1. "Walk me through how you evaluated your RAG system."**
First error analysis: 10 questions by hand, reading chunks, logging why each failed. Then
a 32-question golden set with page + exact-sentence evidence and a strict validator. Then
an automatic harness: Recall@1/3/5, MRR, nDCG on dev; a deterministic abstention check;
warm per-stage latency with p50/p95. Baseline C0: Recall@5 0.842, MRR 0.667, abstention
0.909, p50 total 1.1 s. Every result is saved with the commit and settings.

**B2. "Your Recall@5 is 0.842 but Recall@1 is 0.526. What would you do?"**
The search finds the right chunk but often not first. I would try a cross-encoder
reranker on the top 10 and check that MRR and Recall@1 rise, then report the latency it
costs, one change at a time in the ablation table.

**B3. "Three questions were missed. What did they have in common?"**
Word mismatch: the user said "payload" and "allowed values", the page said "body" and
"predefined values"; one answer was a bullet list spread over chunks. Dense-only search
struggles with that. I would test hybrid search (keywords plus vectors) and query
rewriting, each as a separate row.

**B4. "Your answer for q-007 was 'not found', but retrieval found the right chunk at rank 1.
How?"**
The chunk contained an include marker `{* ...py *}` instead of the code, because the code
lives in separate files we never downloaded. Retrieval passed, generation failed, and the
fix is in ingestion (an include resolver), not in search. This is exactly why I measure
retrieval and generation separately.

**B5. "In your failure log, an answer was correct but you marked it a failure. Why?"**
It showed code labelled "from the docs" that was in no retrieved chunk. The rule was right,
but the code was invented. In RAG, unsupported content is a faithfulness failure even if
it is true; users cannot tell which parts are grounded.

**B6. "Can't you just drop chunks with a low similarity score?"**
I tested that idea with data: an off-topic chunk scored 0.705 and a correct chunk for
another question scored 0.700. A fixed threshold cannot separate them, so abstention has
to come from the LLM reading the context (and later a reranker or grader).

**B7. "How did you choose the unanswerable questions?"**
About 15% of the set, mostly near-misses: topics close to the pages but not in them (422
status code, JWT, `max_length`). Easy off-topic questions would make abstention look better
than it is.

**B8. "Your abstention accuracy is 0.909. Is the LLM the problem?"**
No. False answers were 0 of 3; both errors were false refusals caused upstream: q-007
(include marker) and q-017 (right chunk at rank 6, but only the top 4 reach the LLM). So
the fixes are ingestion and ranking, not the prompt.

**B9. "Why is your golden set only 32 questions? Is that enough?"**
Enough to start and to read every failure; too small for fine comparisons. With 19 scored
questions one question moves Recall by about 5 points, so I treat small differences as
ties. It grows when the corpus widens (at least 10 per domain) and from real failures.

**B10. "How do you stop the test set from leaking into your tuning?"**
Test is run only at phase gates; the 10 failure-log questions sit in dev because I had
already seen them; all experiments are scored on dev.

**B11. "Where does the time go in your system, and what would you optimise?"**
Warm p50 total 1107 ms: LLM about 1060 ms, embedding 16 ms, search 1 ms. So the LLM is
about 96%. Optimising search is pointless; options are streaming (time to first token), a
faster model, caching, or shorter prompts.

**B12. "Your latency run showed 15 rate-limit retries. How did you handle that in the
numbers?"**
I turned off the client library's silent retries and counted them myself. I report
`total` (the successful request) and `wall_with_retries` (including the waits: p50 5.9 s)
separately, because the waits are real user pain on a free tier.

**B13. "How do you make sure a typo in the answer key doesn't corrupt your scores?"**
A validator checks that every evidence sentence appears character for character in its
page, plus fields, ids and splits. It runs before every eval; the runner refuses to score
if the set is invalid. Tests prove it catches a one-character typo.

**B14. "How do you know which code produced a number?"**
Every result file stores the git commit and adds `+dirty` if there were uncommitted
changes. I commit first, then run. Settings and per-question rows are in the same file.

**B15. "A teammate says the new chunking improved Recall@5 from 0.842 to 0.86. Do you
merge?"**
Not on that alone. On 19 questions 0.842 is 16 and 0.895 would be 17; 0.86 is not even a
possible value with n=19, so I would first check n and the dataset version. Then I would
read which questions changed, check MRR and latency, and confirm on a larger set or at the
gate on test.

**B16. "How would you add evals to CI without spending money?"**
Only deterministic retrieval evals on a small fixed corpus: no LLM, same result every run.
The PR fails if Recall@5 or MRR drops below baseline minus a tolerance. LLM-judged evals
run by hand or nightly. (Phase 2.10.)

**B17. "How will you evaluate the system after deployment?"**
No answer key online, so monitor signals: refusal rate, p95 latency, error and 429 rates,
user feedback, new question types. Sample real conversations, label them, and add
failures to the golden set as regression tests.

**B18. "Why did you write Recall and MRR yourself instead of using RAGAS?"**
To understand and test them: each formula has hand-computed unit tests. Later I compare my
numbers with RAGAS/DeepEval and can explain any difference instead of trusting a black box.

**B19. "If you had to give one number for your system's quality, which would it be?"**
I would refuse to give only one: Recall@5 for finding, MRR for ranking, abstention for
honesty, faithfulness for grounding (Phase 3.9), and p95 latency for speed. Each catches a
different failure; one number hides the others.

**B20. "What surprised you most when you evaluated your RAG?"**
That the retrieval was decent but the chunk content was the problem, and that a fully
correct-looking answer contained invented code. Without reading chunks and checking
grounding, both would have been invisible.

---

## C. Do it by hand (whiteboard practice)

Work each one on paper, then check the answer.

**C1.** Relevance `[0, 0, 1, 0, 0]`. Recall@1, Recall@3, Recall@5, reciprocal rank?
> 0, 1, 1, 1/3 = 0.333.

**C2.** Three questions with reciprocal ranks 1, 0.5, 0. MRR?
> (1 + 0.5 + 0) / 3 = 0.5.

**C3.** Recall@5 is 0.842 on 19 questions. How many questions were found?
> 0.842 x 19 = 16.

**C4.** A question has 2 golden sentences; only one is found, at rank 1. Strict Recall@5?
> 1 / 2 = 0.5.

**C5.** One golden sentence found at rank 3. nDCG@5?
> 1/log2(4) = 0.5; ideal = 1; nDCG = 0.5.

**C6.** Latencies (ms): 100, 120, 110, 900, 105. p50 and the max? Why is the average
misleading?
> Sorted: 100, 105, 110, 120, 900. p50 = 110, max = 900. Average = 267, which no request
> took.

**C7.** 22 questions, 3 unanswerable. The system refuses 3 answerable questions and answers
1 unanswerable one. Abstention accuracy? Both error counts?
> Wrong = 3 + 1 = 4; accuracy = 18/22 = 0.818. False refusals 3/19, false answers 1/3.

---

## D. Your 60-second answer: "Tell me about evals in your project"

> "In DocPilot, a RAG assistant over FastAPI docs, I built the evals before any advanced
> feature. I started with error analysis on 10 questions, which showed the main problems
> were in the chunks, not the search, and caught an answer that invented code. Then I
> built a 32-question golden set labelled by page and exact sentence, with dev/test
> splits, about 15% trick questions, and a validator. My harness scores retrieval with
> Recall@k, MRR and nDCG, checks abstention with plain code, and measures warm p50/p95
> latency per stage. The baseline is Recall@5 0.842 but Recall@1 only 0.526, so ranking is
> the weak spot; abstention 0.909 with zero made-up answers; p50 1.1 s with the LLM taking
> about 96% of the time. Every number is tied to a git commit, and each later improvement
> is one row in an ablation table against this baseline."

Update the numbers in this answer each time a new row is added to `evals/ABLATION.md`.

---

## E. Words to use (and to avoid)

| Say | Instead of |
|---|---|
| "on 19 dev questions, Recall@5 went from 0.842 to X" | "it got better" |
| "p95 total 1.76 s, warm, laptop CPU, n=22" | "it's fast" |
| "unsupported by the retrieved context" | "the AI lied" |
| "a tie at this sample size" | "slightly better" |
| "false refusal / false answer" | "it failed sometimes" |

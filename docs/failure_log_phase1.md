# Failure Log, Phase 1 (naive baseline C0)

Step 1b of [implementation_plan/2_phase_1_baseline.md](implementation_plan/2_phase_1_baseline.md).
Goal: watch naive RAG fail with your own eyes **before** measuring anything. The rows are
filled from real `03_ask.py --full` output. On 2026-10-12 the learner asked the mentor to
run all 10 and write the notes; the learner rewrites the three summary lines in their own
words before the Phase 1 gate.

**Setup (do not change during this step):** 4 FastAPI pages at commit `d62354434b2e`
(D-029), chunks 800/100 characters, `BAAI/bge-small-en-v1.5`, top_k 4, Groq
`openai/gpt-oss-120b` (D-028). Date of run: 2026-10-12. Git commit: `bb4709f` + uncommitted `03_ask.py` (`--full`, UTF-8
fix). Index: 51 chunks. Raw outputs were not committed (they contain doc text).

---

## How to fill a row

1. **Before running:** write your prediction for the question (correct answer? right chunk
   in the top 4?) and **one reason**, in the "Prediction" column.
2. Run it: `python scripts/03_ask.py --full "question"` (`--full` prints whole chunks).
3. Open the page from the answer key below and find the passage that holds the answer.
4. **Right chunk in top 4?** = does one of the 4 printed chunks contain that passage?
   Write `yes, rank N` or `no`.
5. **Answer correct?** = correct **and** supported by the retrieved chunks. An answer that
   is true in real life but does not appear in any chunk counts as `no (ungrounded)`.
   Before you mark a number or a fact as correct, search the 4 pages for it.
6. **What went wrong:** your own words, and name the evidence (chunk number, the line you
   saw). "Nothing" is a valid answer if nothing went wrong.

---

## The 10 questions

| # | Question | Type | Prediction (before run, with a reason) | Answer correct? | Right chunk in top 4? | What went wrong (your words) |
|---|---|---|---|---|---|---|
| 1 | How do I make a query parameter optional? | how-to | "perfect answer from the docs" (no reason) | **partly**: rule right (default `None`), but it shows code labelled "Example (from the docs)" that is in no chunk and no page | yes, rank 2 (`query-params #2`) | Ungrounded code: the chunk has only the `{* ...tutorial002... *}` marker, so the LLM wrote its own example and claimed it came from the docs. Rank 1 (`#6`) only mentions "optional". Citation printed as `【2】`, not `[2]` |
| 2 | How do I connect FastAPI to a PostgreSQL database? | not-in-docs | "it will say it is not in the document" (no reason) | yes: exact `NOT_FOUND` | n/a (no right chunk exists) | Nothing wrong in the answer. But search still returned 4 chunks, top score **0.705**, higher than the correct chunk in Q5 (0.700). The LLM abstained, not the search |
| 3 | What status code does FastAPI return on validation failure? | factual | "retrieved text + some LLM content" (no reason) | yes: `NOT_FOUND`, and that is right: "422" is on none of the 4 pages | `path-params #2` (Data validation) at rank 3; it shows the error body, not a status code | Prediction was wrong here: the LLM did **not** add its own knowledge, though it did in Q1. Same model, same prompt, different behaviour: one hand test proves nothing |
| 4 | What does `{file_path:path}` mean in a route? | exact identifier | n/a | yes | yes, rank 1 (`path-params #11`) | Nothing. Exact text `{file_path:path}` in the question and in the chunk; meaning search was enough on 51 chunks |
| 5 | My route for the current user keeps getting caught by the route that takes a user ID. Why? | paraphrase | n/a | yes | yes, rank 1 (`path-params #6`) | Nothing in the answer. The chunk starts mid-sentence ("the path for `/users/me` is declared before..."); the reason sentence sits in chunk #5. Top score 0.700, lower than Q2's irrelevant 0.705. Ranks 2-4 off-topic (`first-steps`) |
| 6 | How does FastAPI decide if a function parameter is a path parameter, a query parameter or the request body? | comparison | n/a | yes | yes, rank 2 (`body #8`); rank 1 `body #7` holds the first half | The 3-rule list is cut across chunks #7 and #8; the 100-char overlap saved it this time |
| 7 | Show me the code for a minimal FastAPI app. | code | n/a | **no**: `NOT_FOUND` for a question the real docs answer | rank 1 (`first-steps #0`), but it holds `{* ../../docs_src/first_steps/tutorial001_py310.py *}`, not code | Known failure 1 (include markers). Honest abstention, but the system failed: the code was never downloaded. Same chunk has HTML (`<font color=...>`, `<span style=...>`), known failure 3 |
| 8 | Which values in the URL make a `bool` query parameter `True`? | table/list | n/a | yes (1, true, on, yes, any case) | yes, rank 1 (`query-params #3`) | Nothing. Expected a cut list; the whole list fit in one 800-char chunk |
| 9 | Where can I see the automatic interactive documentation for my API? | factual | n/a | yes (`/docs`, Swagger UI); did not mention `/redoc` although rank 2 had it | yes, rank 1 (`first-steps #5`) | Minor: incomplete. The HTML terminal chunk did not reach the top 4. Citation `【1】` again |
| 10 | Can I restrict a query parameter to fixed values the same way as a path parameter? | multi-hop | n/a | **partly**: "yes, with an `Enum`" is right, but no *how* | half: query side rank 3 (`query-params #6`, the tip); path side ("Predefined values") not in top 4 | Multi-hop: the answer needs a second page the question does not describe. All top 4 came from `query-params` |

### Answer key (where the answer lives; written from reading the pages, not from a run)

| # | Page | Section heading | What a good answer must contain |
|---|---|---|---|
| 1 | `query-params.md` | Optional parameters | default value `None` |
| 2 | none | none | `NOT_FOUND` (no database page was downloaded) |
| 3 | `path-params.md` | Data validation | judge it yourself: search the 4 pages for the number the LLM gives |
| 4 | `path-params.md` | Path convertor | the parameter matches any path (Starlette option) |
| 5 | `path-params.md` | Order matters | declare `/users/me` before `/users/{user_id}`; routes are checked in order |
| 6 | `body.md` | Request body + path + query parameters | path if in the path; singular type = query; Pydantic model = body |
| 7 | `first-steps.md` | top of the page (and Recap, step by step) | real Python code, not a `{* ... *}` marker |
| 8 | `query-params.md` | Query parameter type conversion | the list of accepted spellings (several URL examples) |
| 9 | `first-steps.md` (also `path-params.md`) | Interactive API docs | `http://127.0.0.1:8000/docs` (and `/redoc` as the alternative) |
| 10 | `query-params.md` + `path-params.md` | end of query-params; Predefined values | yes, with an `Enum`; needs both pages to explain how |

Why these 10: they cover each question type the plan asks for (PROJECT_DOCUMENTATION
section 2) and the three known failures (section 18.3): include markers instead of code
(Q7), chunks cut mid-structure (Q8, a list spread over many short code blocks) and HTML
noise (Q9, the terminal screenshot in `first-steps.md`). Q1 and Q2 are the two step 1a.8
questions, so they are not run twice.

---

## Three lines (write after all 10 rows)

Final version for the Phase 1 gate (2026-10-15). Written by the mentor at the learner's
request (no time); confirmed by the 1d evals. Learner: practise saying these aloud.

- **Most common failure:** the search usually found the right page, but **what was inside
  the chunks** was broken: code replaced by `{* ... *}` markers (Q1, Q7), sentences and
  lists cut in the middle (Q5, Q6), HTML noise (Q7). The 1d evals agree: Recall@5 0.842
  but Recall@1 only 0.526, so the remaining search problem is **ranking**, plus word
  mismatch ("payload" vs "body", "allowed" vs "predefined": q-017, q-023).
- **Most surprising failure:** Q1. The answer looked perfect, but it showed code that was
  in no chunk and called it "from the docs": a correct-looking hallucination. Second
  surprise: similarity scores cannot separate good from bad chunks (an off-topic chunk
  scored 0.705, a correct one 0.700), so a score cut-off is not a fix.
- **Which Phase 2/3 feature would fix it, and why:** first the **include resolver (2.3)**
  and **cleaner (2.2)**, because the cause is in the chunk text and both false refusals of
  the abstention check trace back to it (q-007); then **structure-aware chunking (2.4,
  2.6)** so sentences and lists stay whole; in Phase 3 a **reranker** for the weak rank 1
  and **hybrid search / query rewriting** for word mismatch; a **faithfulness eval (3.9)**
  to catch answers like Q1. Multi-hop (Q10) waits for agentic retrieval (Phase 4).

**Caution:** 51 chunks from 4 pages is a tiny haystack, so good retrieval here proves
little. Numbers come in 1d; harder retrieval comes when the corpus widens in 2.8.

**Side findings (not RAG failures):**
- `03_ask.py` crashed with `UnicodeEncodeError` when output went to a file on Windows
  (cp1252 cannot print the 🎉 in the docs or the U+202F in an LLM answer). Fixed with
  `sys.stdout.reconfigure(encoding="utf-8")`.
- The model cites as `【n】` in 3 of 10 answers instead of `[n]`. Code that parses
  citations later (3.9) must accept both, or the prompt must be tightened.

These become golden questions in step 1c (the 10 here + about 20 new ones).

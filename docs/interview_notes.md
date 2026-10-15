# My Interview Notes (in my own words)

This file is written by the learner, not by the AI. At every phase gate, close the model
answers in `docs/interview/`, then answer the questions below from memory, in your own words,
with your own numbers from `evals/ABLATION.md`. If you cannot answer one, that is the part to
study again.

Rule: no copy-paste from the model answers. An interviewer can tell.

> **Honest status (2026-10-15):** the Phase 0 and Phase 1 answers below are **mentor drafts**,
> written at the learner's request (no time) so both gates could close. They are not yet
> in the learner's own words. Before any interview: read each answer once, close the file,
> say it out loud, then rewrite it in your own words here. Full model answers with more
> detail: `docs/teaching/2_evals_guide.md` and `docs/interview/`.

---

## Phase 0

**Lab 2 in two sentences:** Keyword search found the `max_length` question (the exact word
was in doc 1) but scored zero on every doc for "how do I check incoming data is correct",
because that question shares no words with any doc. Meaning search got both right (0.742
and 0.659 for the right docs), because embeddings compare meaning, not spelling; but its
margin on the paraphrase was small (0.659 vs 0.578).

1. **What is an embedding? Explain it to a 10-year-old.**
   It is a list of numbers that describes what a sentence means, like map coordinates for
   ideas. Sentences that mean similar things get coordinates close together, so we can
   find related text by measuring distance. Our model gives 384 numbers per sentence.

2. **Why does meaning search beat keyword search on paraphrases, and lose on exact names?**
   Paraphrases use different words for the same idea; keywords need the same words, so they
   miss, while embeddings still land close together. Exact names like `max_length` or an
   error code are rare tokens: keyword search matches them perfectly, but an embedding can
   blur them with similar-looking names (`min_length`). That is why hybrid search combines
   both (Phase 3).

3. **Why do retrieval models handle queries and documents differently?**
   A question and its answer do not look alike: "how do I make it optional?" vs "set the
   default to None". BGE was trained with an instruction prefix on the question side only,
   so the question vector moves toward answer-style text. In Lab 1 a restated question
   scored higher (0.799) than the real answer sentence (0.708): that gap is the problem the
   prefix addresses.

4. **What happens to a retriever if you feed it the same document twice?**
   Both copies get almost the same vector, so both come back in the top-k and waste a slot
   that a different, useful chunk could have used. In DocPilot each chunk gets a stable id
   (uuid5 of source + chunk number) and we upsert, so re-running ingest never duplicates
   (a test checks this).

## Phase 1

1. **Walk me through your baseline pipeline, file by file.**
   - `config.py`: every setting in one place (chunk 800/100, model + pinned revision,
     top-k 4, exact "not found" sentence); secrets come from `.env`.
   - `loader.py`: reads the `.md` files in a stable order.
   - `chunker.py`: fixed-size pieces of 800 characters with 100 overlap (a weak baseline on
     purpose).
   - `embedder.py`: BGE-small, 384 numbers per chunk; the query prefix is added by hand.
   - `vector_store.py`: Qdrant in local mode; fresh collection, upsert, `query_points`.
   - `llm.py`: one OpenAI-compatible client pointed at Groq (`gpt-oss-120b`), temperature 0,
     fails loudly on an empty answer.
   - `rag.py`: embed question -> search top 4 -> numbered context -> LLM -> answer with
     citations, plus timings per stage.
   - Scripts: download (pinned commit), ingest (51 chunks), ask. `api.py`: the same `ask()`
     behind `POST /ask`.
   - `evals/`: golden set, validator, matching, metrics, three runners, ablation table.

2. **What is Recall@5 and what was your C0 value?**
   The share of questions where at least one chunk holding the answer is in the top 5
   results. C0 on dev: **0.842** (16 of 19); on test: 1.000 (8 of 8). But Recall@1 was only
   0.526 on dev and MRR 0.667: the search finds the right chunk but often does not put it
   first, so ranking (a reranker) is the next thing to try.

3. **Why label gold evidence by snippet and not by chunk id?**
   Chunk ids depend on how the text was cut; change the chunking and chunk 7 is different
   text. A short sentence copied exactly from the page stays the same, so one answer key
   can score every chunking strategy in Phase 2. A validator checks every snippet really
   is in its page, because one typo would silently turn a hit into a miss.

## Phase 2
1. Which chunking strategy won, by how much, and on which question types?

## Phase 3
1. What did hybrid search and the reranker each add, and what did the reranker cost in latency?

## Phase 4
1. Where did the agentic loop help, where did it not, and what did it cost in LLM calls?

## Phase 5
1. How does your human-in-the-loop survive a server restart?

## Phase 6
1. Attack success rate and false-block rate before and after guardrails?

## Phase 7
1. Draw your production architecture and walk through one request.

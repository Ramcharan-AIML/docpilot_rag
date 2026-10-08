# My Interview Notes (in my own words)

This file is written by the learner, not by the AI. At every phase gate, close the model
answers in `docs/interview/`, then answer the questions below from memory, in your own words,
with your own numbers from `evals/ABLATION.md`. If you cannot answer one, that is the part to
study again.

Rule: no copy-paste from the model answers. An interviewer can tell.

---

## Phase 0
1. What is an embedding? Explain it to a 10-year-old.
2. Why does meaning search beat keyword search on paraphrases, and lose on exact names?
3. Why do retrieval models use different handling for queries and documents?
4. What happens to a retriever if you feed it the same document twice?


## Phase 1
1. Walk me through your baseline pipeline, file by file.
2. What is Recall@5 and what was your C0 value?
3. Why label gold evidence by snippet and not by chunk id?

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

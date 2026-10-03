# Interview Questions, Phase 4: Agentic RAG and LangGraph

---

### Q1. "What makes your RAG 'agentic'?"

**Model answer:** "At some steps, the LLM's output decides what happens next. A router decides
whether to retrieve or answer directly; a grader judges whether retrieved chunks are
relevant; if none are, a rewriter reformulates the query and we retry, at most twice; after
generation, a groundedness check can trigger one regeneration, or abstention. It is a
controlled graph, not a free-roaming agent: every loop has a cap and every LLM output is
validated."

---

### Q2. "Hybrid RAG vs agentic RAG?"

**Model answer:** "Different axes. Hybrid is how we search: keyword plus meaning, fused.
Agentic is who controls the steps: fixed code, or an LLM making decisions. You can have
either without the other. I added hybrid in Phase 3 and agentic in Phase 4, each justified
by evals."

---

### Q3. "When should you NOT use agentic RAG?"

**Model answer:** "For simple lookups, where plain retrieval already finds the answer.
The agentic path added [n/a] LLM calls and [n/a] ms p95 per question; it helped on
[types, n/a] and did nothing on [types]. So my router sends simple questions down the cheap
path. I set the keep/drop rule before looking at the numbers to avoid justifying what I had
already built."

**This is one of the strongest answers in the whole project.**

---

### Q4. "Why LangGraph?"

**Model answer:** "Explicit state, nodes, and conditional edges, so the control flow is
visible and testable; checkpointers that save state after each step; and `interrupt` for
human-in-the-loop with resume after restarts. I first wrote the loop in plain Python, about
40 lines, so I knew what LangGraph was doing for me. LlamaIndex is great for RAG pipelines
but less direct for agent state and HITL; CrewAI and AutoGen give less control over exact
steps and checkpoints."

---

### Q5. "How do you stop infinite loops and runaway cost?"

**Model answer:** "Four layers: per-loop caps (2 rewrites, 1 regeneration), a per-question
LLM-call budget, timeouts on every LLM call, and LangGraph's recursion limit as a last
safety net. If a cap is hit, the answer is the not-found phrase or a human review, never a
guess. Unit tests with a scripted fake LLM prove each cap without spending tokens."

---

### Q6. "Small free models are bad at JSON. How did you handle structured outputs?"

**Model answer:** "Pydantic schemas for every LLM decision. Ask for JSON with the exact
shape; validate; on failure retry once with the validation error in the prompt; if it still
fails, use a safe default per node. Where the provider supports JSON mode or tool calling,
I use it, but I still validate. I tracked the parse-failure rate: [n/a]."

---

### Q7. "What happens if the grader itself breaks?"

**Model answer:** "It fails open: keep all chunks, log it. Throwing away good chunks would
guarantee a bad answer. The groundedness check fails closed: low confidence, abstain or
send to a human, because an unchecked answer shown confidently is the worse failure. Each
node has a reasoned default, written in the decision log."

---

### Q8. "How do you test an agent?"

**Model answer:** "Two separate things. Control logic: unit tests with a fake LLM returning
scripted outputs, so routing, caps, and counters are tested exactly and for free. Quality:
evals with the real LLM, comparing agentic and non-agentic on faithfulness, relevancy,
abstention, latency, and calls per question, per question type."

---

### Q9. "RAGAS or DeepEval: how did they compare with your own judge?"

**Model answer:** "I ran [library] on the same items as my own judge. Agreement was [n/a].
Where they disagreed, I checked by hand: [finding]. I kept [choice] because [reason]. The
libraries give standard metric definitions; my own harness let me understand and debug
them."

---

### Q10. "Explain CRAG and Self-RAG briefly."

**Model answer:** "Corrective RAG grades retrieved documents and, if they are poor, corrects
course: rewrite the query, search again, or use another source. Self-RAG has the model
reflect on its own retrieval and generation, checking whether output is supported. My
grade-and-rewrite loop is CRAG-style, and the groundedness check is Self-RAG-style, both
simplified and capped."

---

### Q11. Trap: "Agents are the future. Why not make everything agentic?"

**Model answer:** "Because every LLM decision adds latency, cost, and a new way to fail, and
makes behaviour harder to test. I use them where evals show a gain. A fixed pipeline that
works is better engineering than an agent that sometimes works. My numbers: [n/a]."

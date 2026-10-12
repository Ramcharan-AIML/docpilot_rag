# Interview Questions, Phase 1: Baseline RAG, Evals, Mini API

---

### Q1. "Walk me through what happens when a user asks DocPilot a question." (baseline version)

**Testing:** do you actually know your system end to end.

**Model answer:** "The question is embedded with bge-small plus the BGE query prefix.
Qdrant returns the 4 nearest chunks by cosine similarity. I number them [1] to [4] with
their source and put them in the prompt with a system prompt saying: use only this
context, cite numbers, and if the answer is not there say exactly 'I could not find this
in the documents.' The LLM runs at temperature 0, and I return the answer plus the source
chunks with scores. In code that is `embedder.embed_query`, `vector_store.search`,
`rag.build_context`, and `llm.chat`, glued in `rag.ask`."

**Follow-up:** "And ingestion?" "`loader` reads files, `chunker` cuts 800-character chunks
with 100 overlap, `embedder.embed_documents` embeds in batches without the prefix,
`vector_store` creates a fresh collection and upserts points with stable uuid5 ids."

---

### Q2. "Why RAG and not fine-tuning?"

**Model answer:** "Three reasons. Docs change, and RAG updates by re-indexing in minutes
while fine-tuning means retraining. RAG gives citations because I know which chunk was
used. And it can abstain when nothing relevant is retrieved. Fine-tuning is better for
teaching style or format, not for keeping facts current. Also, I had no GPU budget."

---

### Q3. "Why did you start with fixed-size chunking if you knew it was bad?"

**Model answer:** "On purpose. I needed an honest baseline number, C0, so every later
improvement has a measured size. If I had started with my best guess, I could never say
how much structure-aware chunking actually gave. C0 Recall@5 was [your number: n/a], and
the best Phase 2 strategy reached [your number: n/a]."

**Losing answer:** "That's what the tutorial did."

---

### Q4. "How do you evaluate a RAG system?"

**Model answer:** "In layers. Retrieval first: Recall@k, MRR, nDCG on a hand-written golden
dataset. These are deterministic and free, so they run in CI. Then generation:
faithfulness, answer relevancy, correctness, and abstention accuracy, using an LLM judge
with spot checks. Then agent metrics, guardrail metrics, and system latency. Golden data
has a dev split for daily work and a test split I only run at phase gates, so I do not
overfit to the exam."

---

### Q5. "Explain Recall@k, MRR, and nDCG. Why three?"

**Model answer:** "Recall@k: did any correct chunk appear in the top k. It answers 'could
the LLM possibly answer?'. MRR: the average of 1 over the rank of the first correct chunk;
it rewards putting the right chunk first. nDCG@k: credits every relevant chunk with a
log-discount by position, normalised by the ideal ordering. A change can raise recall but
push the best chunk down, which MRR and nDCG catch."

**Follow-up:** "Compute MRR for two questions whose first hits are at rank 1 and rank 4."
"(1 + 0.25) / 2 = 0.625."

---

### Q6. "How did you build your golden dataset? How do you know the labels are right?"

**Model answer:** "By hand, starting with about 30 questions covering every question type:
factual, how-to, exact identifier, paraphrase, comparison, multi-hop, table or code,
version, unanswerable, and so on. About 15% are unanswerable. Each answerable item has
evidence as a document plus a short verbatim snippet. A validation script checks every
snippet really exists in its document, because a typo silently turns a hit into a miss."

**Follow-up:** "Why snippets and not chunk ids?" "Chunk ids change with every chunking
strategy. A snippet works for all strategies, so one answer key compares them fairly.
A hit is a chunk containing the snippet, or at least 70% of it continuously for snippets
cut by a boundary. Each snippet counts once."

---

### Q7. "30 questions is tiny. Can you trust your numbers?"

**Model answer:** "Only for large differences. With 30 questions, one question moves
Recall by about 3 points, so I treat small gaps as ties. I grew the set to [your size:
n/a], look at per-type results, and read the failing questions instead of trusting the
average. I would add confidence intervals or bootstrap resampling with more time."

**This honest answer impresses more than defending the number.**

---

### Q8. "How does your system avoid hallucinating?"

**Model answer (Phase 1 version):** "Weakly, at this stage: the system prompt tells the
model to use only the context and to say a fixed not-found phrase otherwise, and I measure
abstention accuracy by checking for that exact phrase on unanswerable questions: [your
number: n/a]. Later phases add a document grader, a groundedness check, output guards,
and human review, each measured."

---

### Q9. "Why did you use the OpenAI client library if you don't use OpenAI?"

**Model answer:** "Groq, OpenRouter, Ollama, and Gemini expose OpenAI-compatible endpoints.
One well-maintained client works for all of them, so changing the provider is a config
change. The LLM sits behind a small interface, so a different SDK could replace it in one
file."

---

### Q10. "Why FastAPI? What does Pydantic do for you?"

**Model answer:** "FastAPI gives typed request and response models via Pydantic, automatic
validation with 422 errors before my code runs, automatic interactive docs at `/docs`, and
native async for later. Flask can do these with add-ons. Pydantic models define the API
contract: `question` must be a string between 1 and 2000 characters."

**Follow-up:** "`def` or `async def` for your endpoint?" "In Phase 1, plain `def`, because my
model and LLM calls were blocking; FastAPI runs `def` endpoints in a thread pool. Blocking
code inside `async def` would freeze the event loop. In Phase 7 I moved network calls to
async clients and CPU work to threads."

---

### Q11. "How did you test the API without calling the LLM?"

**Model answer:** "With FastAPI's TestClient and pytest's monkeypatch to replace `ask` with
a fake. The test checks my code: validation and response shape. LLM quality is measured
separately by evals. Unit tests stay fast, free, and deterministic."

---

### Q12. "What failures did you find in the naive baseline?"

**Model answer:** "[From your failure log.] For example, FastAPI docs use include markers
like `{* ../../docs_src/... *}`, so chunks held the marker instead of the code, and 'show me
a minimal app' could not be answered. Chunks were cut through HTML styling, and colour
tags polluted the vectors. These became Phase 2 tasks, each measured."

---

### Q13. Trap: "Your top-k is 4. Why 4?"

**Model answer:** "It was the baseline default, not an optimised value. Larger k raises
recall but adds tokens and noise to the prompt. In Phase 3, I retrieve more candidates
(20-50), rerank, and keep the best few, which separates 'find widely' from 'show the LLM
only the best'. The final value came from the eval: [your number: n/a]."

---

### Q14. "How do you work with Git on this project?"

**Model answer:** "From Phase 1 every change goes through a pull request: a small feature
branch per step, squash-merged into the phase branch, and the phase branch merged into `main`
at the gate. `main` is protected: CI must be green (ruff, pytest, a 500-line file check) and
direct pushes are rejected. I proved it with a PR containing a failing test. Each gate gets an
annotated tag, so anyone can check out exactly the system that produced a given number."

**Losing answer:** "I just commit to main."

---

### Q15. "How fast is your baseline, and where does the time go?"

**Model answer:** "I time every stage inside `ask()`: query embedding, vector search and
the LLM call. On my laptop CPU with Groq gpt-oss-120b, over [n/a] dev questions after a
warm-up call, p50 total was [n/a] s and p95 [n/a] s; the LLM stage was [n/a]% of it, and
retrieval was [n/a] ms. So speeding up search would not help users; the LLM call is the
lever. That baseline, L0, is what later techniques like reranking are charged against."

**Follow-up:** "Why not just report the average?" "Averages hide the slow tail. Rate-limit
retries and cold starts show up in p95, and that is what an unlucky user feels."

**Losing answer:** "It's pretty fast." (No number, no stage, no hardware.)

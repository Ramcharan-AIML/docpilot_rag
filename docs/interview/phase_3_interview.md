# Interview Questions, Phase 3: Retrieval, Reranking, Judges, Docker

---

### Q1. "Why hybrid search?"

**Model answer:** "Dense search misses exact identifiers like `max_length` or error codes;
keyword search misses paraphrases. On my set, dense-only Recall@5 was [n/a], sparse-only
[n/a], hybrid [n/a]. Per type, sparse won on exact-identifier questions and dense on
paraphrases [confirm with your data], and hybrid got the best of both."

---

### Q2. "What is RRF and why did you use it instead of combining scores?"

**Model answer:** "Reciprocal Rank Fusion. Each chunk gets 1 over (k + rank) from each list,
summed; k is usually 60. It uses ranks, not scores, because cosine and BM25 scores are on
different scales and normalising them is fragile. I wrote it by hand first, then used
Qdrant's server-side fusion with prefetch, and checked both gave the same top results."

**Follow-up:** "What does k do?" "A small k makes top ranks dominate; a large k flattens
differences. I tried 60 and [other value]: [n/a]."

---

### Q3. "Bi-encoder vs cross-encoder? Why rerank?"

**Model answer:** "A bi-encoder embeds question and chunk separately, so chunks are embedded
once and search is instant, but it never sees them together. A cross-encoder reads the pair
together and scores relevance more accurately, but must run per pair at query time. So:
cheap wide first pass, expensive narrow second pass. My reranker took the top [n] and
improved MRR from [n/a] to [n/a], adding [n/a] ms p95 on CPU."

**Follow-up:** "How did you choose how many candidates to rerank?" "Measured 20, 30, and 50:
quality vs latency table. [Chosen] because [evidence]."

---

### Q4. "Which query transformations did you try, and which worked?"

**Model answer:** "Multi-query, HyDE, step-back, and decomposition, each as its own row with
LLM calls per question and latency. [Result: n/a]. I cached transformed queries so eval
runs were repeatable and free after the first run."

**Strong version if none helped:** "None beat the reranked hybrid baseline by more than
noise, so I kept none. On clean technical docs with a good reranker, they mainly added
latency and an LLM call."

---

### Q5. "Why Qdrant over pgvector, Chroma, or Pinecone?"

**Model answer:** "I needed dense and sparse vectors with server-side fusion, payload
filters, a Docker image (including ARM), and zero cost. Chroma is easier but had fewer of
these features; pgvector is great if Postgres already holds your data, but hybrid needs more
manual work; FAISS is a library without payloads or a server; Pinecone is managed and
paid. I would choose pgvector if the company already ran Postgres and wanted one database,
and I'd check its hybrid story first."

---

### Q6. "How would you choose an embedding model for a new domain?"

**Model answer:** "Not from a leaderboard. Build a small golden set from the domain, then
compare a few candidates on Recall and MRR against cost: index time, query latency, RAM,
vector size. Use each model's correct prefixes; wrong prefixes quietly lower scores. I did
this with [models]: [n/a]."

---

### Q7. "How do you evaluate the generated answer? Can you trust an LLM judge?"

**Model answer:** "Faithfulness (are claims supported by context), answer relevancy,
correctness against a reference, and abstention accuracy. The judge lists claims, then checks
each one, which is more reliable than one score. I do not trust it blindly: temperature 0, a
different model from the generator to reduce self-preference, the strongest free judge I
could get, about 20% of items checked by hand, and I report agreement with my hand labels:
[n/a] — and the judge model name with every number."

**Follow-up:** "Faithful but irrelevant?" "Accurate quotes about path params when asked about
query params: all claims supported, question not answered."

---

### Q8. "How do metadata filters work and why not filter after search?"

**Model answer:** "Payload fields like technology and version are indexed in Qdrant, and the
filter is applied during the search. Filtering after a top-4 search might leave one result.
v1 extracted the technology with keywords; the router can extract it with an LLM."

---

### Q9. "What is Docker, and why did you move Qdrant into it?"

**Model answer:** "Docker packages a program with everything it needs, so it runs the same
everywhere. An image is the template, a container is a running copy, a volume keeps data
outside the container. Local-mode Qdrant only allows one process, so the API and the ingest
script could not run together; the Docker server fixed that and matches production. I pinned
the image tag and checked it supports arm64 for the free ARM VM."

---

### Q10. "What's the latency budget of your retrieval?"

**Model answer:** "Measured per stage with p50/p95 on my CPU: query embedding [n/a], hybrid
search [n/a], reranking [n/a]. The reranker dominated, so [decision]. Without these
numbers I could not have reasoned about the trade-off."

---

### Q11. Trap: "Why not just increase top-k to 20 and let the LLM figure it out?"

**Model answer:** "More context means more tokens (cost, latency, free-tier limits) and more
irrelevant text, and models are known to use information in the middle of long contexts
less reliably. Reranking keeps recall from the wide search but shows the LLM only the best
few chunks. I'd test top-k on the generation metrics before claiming either way."

# Interview Questions, Phase 0: Foundations

---

### Q1. "What is an embedding? Explain it like I am not technical, then technically."

**Testing:** can you explain simply and precisely.

**Model answer:** "Simply: it is a set of map coordinates for meaning. Sentences that mean
similar things land close together on the map. Technically: a model such as
bge-small-en-v1.5 converts text into a fixed-length vector, 384 numbers in my case. It was
trained with pairs of related texts so that related texts get vectors pointing in a similar
direction. I compare them with cosine similarity."

**Follow-up:** "What happens if the text is longer than the model accepts?"
"It is truncated silently at the model's maximum token length, so the end of the text is
not represented. That is why I measured chunk sizes in model tokens in Phase 2."

**Losing answer:** "It turns words into numbers." (True but shows no understanding.)

---

### Q2. "Why cosine similarity and not Euclidean distance?"

**Model answer:** "Cosine compares direction and ignores vector length; for these
embedding models, direction carries the meaning. When vectors are normalised to length 1,
cosine equals the dot product, and Euclidean distance ranks results in the same order
anyway, so normalised vectors make the choice mostly about speed and convention. I
normalise at encode time and configure Qdrant with cosine distance."

**Follow-up:** "Is a cosine score of 0.8 good?" "Only relative to other scores from the same
model. Scores are for ranking, not probabilities. Different models have different
typical ranges."

---

### Q3. "Why did you choose bge-small-en-v1.5?"

**Model answer (C-A-E-T):** "I needed a free embedding model that runs on CPU, since my
GPU is too small. Alternatives were paid APIs (cost, and data leaves the machine) and
bigger open models like bge-base, bge-m3, nomic, and e5. bge-small is small, fast, and
strong for its size, so I started with it, and in Phase 3 I compared the others on my own
eval: [your number: n/a]. I kept [model] because [quality vs latency evidence]."

**Losing answer:** "It was top of the leaderboard." (Leaderboards average other domains.
Your data decides.)

---

### Q4. "When does keyword search beat semantic search, and vice versa?"

**Model answer:** "Keyword search wins on exact, rare tokens: function names like
`max_length`, error codes, flags, because it matches characters exactly and BM25 weights
rare words heavily. Semantic search wins on paraphrases: 'check incoming data is correct'
matches a page about validation with few shared words. I saw both in my own lab, which is
why I added hybrid search later."

---

### Q5. "What is the BGE query prefix?"

**Model answer:** "BGE v1.5 models were trained with an instruction prepended to queries
for retrieval. I add it to questions only, never to documents. Forgetting it lowers
retrieval quality without any error, so I later used 'remove the prefix' as the
deliberately bad change that proved my CI eval gate catches regressions."

---

### Q6. "How do you manage secrets and dependencies in your project?"

**Model answer:** "Secrets live in a `.env` file that is gitignored; I commit
`.env.example` with empty values. In CI they come from GitHub Secrets, on the server from
an env file copied by hand. If a key were ever pushed, I would revoke it at the provider;
deleting the commit is not enough. Dependencies are pinned with exact versions, and every
new dependency needed a decision-log entry with the alternative I rejected."

---

### Q7. Trap: "Why not just use the OpenAI embeddings API? It is better."

**Model answer:** "It may score higher on some benchmarks, but it costs money, sends our
documents to a third party, and adds network latency on every query. My constraint was
zero cost and local data. More importantly, I would not assume 'better' without measuring
on my own eval. If a client needed the best quality and allowed paid APIs, I would add it
behind the same `Embedder` interface and compare on the same golden set."

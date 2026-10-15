# Interview Questions, Phase 8: Stretch Topics

Answer these only about what you actually tried. For anything you did not build, say so and
explain the idea and the trade-off. Honest "I know how it works but didn't build it" beats
pretending.

---

### Q1. "What is GraphRAG? Did you use it?"

**Model answer:** "GraphRAG builds a knowledge graph of entities and relations, usually with
an LLM reading every chunk, and uses it for multi-hop and big-picture questions. It is
expensive to build and rebuild on free tiers. I built a lite version from explicit links
already in the docs, at zero LLM cost: after retrieval I pull in up to two linked sections and
rerank. On multi-hop questions it moved Recall@5 from [n/a] to [n/a] [or: I did not build it]."

---

### Q2. "What is DSPy?"

**Model answer:** "A framework that treats prompts and few-shot examples as parameters and
optimises them against a metric on a dataset. The risk is overfitting to the dev set or to
the judge's quirks, so optimise on dev, check test once, and spot-check by hand.
[Your result or: not tried.]"

---

### Q3. "ColBERT vs bi-encoder vs cross-encoder?"

**Model answer:** "Bi-encoder: one vector per text, compared once, fastest. Cross-encoder:
reads the pair together, most accurate, slowest. ColBERT: one vector per token and
'late interaction' (each question token matched to its best chunk token), between the two in
accuracy and cost, with a much bigger index."

---

### Q4. "What is ColPali?"

**Model answer:** "Retrieval over images of document pages with a vision-language model, so
diagrams and layout are searchable without OCR. Heavy for a CPU-only setup, which is why I
[did not use it / measured it at n/a]."

---

### Q5. "What are trajectory evals?"

**Model answer:** "Grading the path an agent took, not just its answer: expected nodes and
tools vs actual, unnecessary rewrites or tool calls. It catches agents that are right by luck
after wasted steps."

---

### Q6. "Kubernetes or Compose for this project?"

**Model answer:** "I used both: Compose for local development, k3s for production on one VM
(rolling updates gated by readiness probes, restarts, CronJobs). Kubernetes pays off fully
with many nodes, autoscaling, and teams. Details are in the Phase 7 answers."

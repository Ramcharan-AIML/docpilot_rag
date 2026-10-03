# Teaching Notes, Phase 8: Stretch Topics

Plan file: `docs/implementation_plan/phase_8_stretch.md`. Optional, only after Phase 7.

---

## 1. GraphRAG and GraphRAG-lite

**Like I'm five:** normal RAG finds the right pages. GraphRAG also follows the "see page
42" notes between pages, so it can answer questions that need two pages joined together.

**Full GraphRAG:** an LLM reads every chunk and extracts entities and relationships into a
knowledge graph, often with community summaries. Strong for "big picture" and multi-hop
questions; expensive (many LLM calls), and must be rebuilt when docs change.

**Our lite version:** docs already contain explicit links ("see Path Parameters"). We use
those as edges, at zero LLM cost. After retrieval, we pull in a couple of linked sections
and rerank. Measure on multi-hop questions, and check it does not hurt the rest.

## 2. DSPy

**Like I'm five:** instead of you rewriting the prompt by hand 30 times, a program tries
many prompt versions (and example selections) and keeps the one that scores best on your
exam.

DSPy treats prompts as parameters to optimise against a metric (our judge). Risks: many
LLM calls (rate limits), overfitting to dev or to the judge's quirks. Optimise on dev, test
once, spot-check by hand.

## 3. ColBERT (late interaction)

Bi-encoders squeeze a chunk into **one** vector. ColBERT keeps **one vector per token** and
matches each question token against its best chunk token ("MaxSim"), then sums.
More precise (especially for exact terms) at the cost of a much larger index.
Sits between bi-encoders (fast, rough) and cross-encoders (slow, precise).

## 4. ColPali (multimodal retrieval)

Embeds **images of PDF pages** directly (text, layout, diagrams together) with a
vision-language model, so a question can match a diagram. Heavy model: likely too slow on
our CPU, so verify before trying. Useful mostly for PDFs where meaning lives in pictures.

## 5. Agent trajectory evaluation

Final-answer metrics miss **how** the agent got there. Trajectory evals compare the actual
path (from traces) to an expected path: unnecessary rewrites, wrong tools, extra loops.
An agent that is right by luck after wasted steps costs money and will fail elsewhere.

## 6. Kubernetes (k3s)

**Like I'm five:** Compose is a to-do list for one kitchen. Kubernetes is a manager for a
chain of kitchens: it decides which kitchen cooks what, replaces sick cooks automatically,
and scales up at lunch rush.

Concepts: **Pod** (one or more containers), **Deployment** (keep N pods running, rolling
updates), **Service** (stable name/IP for pods), **Ingress** (HTTP routing from outside),
**ConfigMap / Secret** (settings and secrets), **StatefulSet** (pods with stable storage,
for databases). k3s is a lightweight distribution that fits a small VM. For one small
deployment, Compose is the right tool; k3s here is for learning.

## 7. Self-check

1. GraphRAG vs GraphRAG-lite: what does each cost?
2. What does DSPy optimise, and what is the overfitting risk?
3. Where does ColBERT sit between bi-encoders and cross-encoders?
4. Why evaluate trajectories and not only answers?
5. When is Kubernetes overkill?

# Interview Questions, Phase 7: Production, Deployment, CI/CD, Observability

---

### Q1. "Draw your production architecture and walk me through one request."

**Model answer:** "Caddy terminates HTTPS and forwards to the FastAPI container. Middleware
assigns a request id and starts a trace. Auth hashes the API key and looks it up in Postgres.
A Redis counter enforces the rate limit. Pydantic validates the body. Exact cache, then
semantic cache [if kept]. Then the LangGraph agent: input guard, router, hybrid retrieval with
reranking, grading, maybe a rewrite, generation through the LLM gateway with fallbacks,
groundedness check, maybe human review with a Postgres checkpoint, output guard. The result
is cached if eligible, metrics and the trace are recorded, and the response returns with
citations and a status. Qdrant, Redis, Postgres, Prometheus, and Grafana run in Compose on an
ARM VM; only Caddy is public."

---

### Q2. "How do you handle free-tier rate limits?"

**Model answer:** "Several layers: an LLM gateway with an ordered fallback list (Groq, Gemini,
OpenRouter free, local Ollama) with retries, exponential backoff with jitter, and a cooldown
for providers that just rate-limited us; caching so repeat questions cost nothing; per-question
LLM-call budgets in the agent; and per-key rate limits so one user cannot exhaust the quota.
I wrote the fallback by hand first, then moved to LiteLLM. Load test: [n/a] fallbacks, zero
5xx when the first provider failed [verify]."

---

### Q3. "What are the risks of a semantic cache?"

**Model answer:** "A wrong hit serves a confident wrong answer. 'Make a query parameter
optional' and 'required' are close in embedding space but have opposite answers. I built
near-miss and paraphrase pairs and measured false-hit and true-hit rates per threshold:
[n/a]. I [kept it at threshold X / disabled it] because [evidence]. Cache keys include prompt,
model, and settings versions so old answers expire after changes."

---

### Q4. "What does your CI pipeline do?"

**Model answer:** "On every PR: ruff lint and format check, pytest, a 500-line file check,
pip-audit, and a retrieval eval gate. The gate indexes a small committed corpus, runs the
deterministic retrieval eval, and fails if Recall@5 or MRR drops below baseline minus a
tolerance. It uses no LLM tokens. I proved it by opening a PR that removed the BGE query
prefix: the gate failed [screenshot]. On merge to main, a workflow builds an arm64 image,
pushes to GHCR tagged with the commit SHA, deploys over SSH with compose pull and up, and
smoke-tests `/ready`. Generation evals run nightly or manually."

---

### Q5. "Why gate only on retrieval metrics?"

**Model answer:** "They are deterministic and free, so a failure means a real regression, not
judge noise or a rate limit. Generation evals use scarce tokens and an LLM judge with
run-to-run variation; they run on a schedule and at gates and inform decisions, but they
don't block merges."

---

### Q6. "How do you observe the system in production?"

**Model answer:** "Structured JSON logs with request ids; Prometheus metrics (request counts,
latency histograms per endpoint and per graph node, LLM calls by provider, fallbacks, cache
hits, guard blocks by reason, review queue size) shown in Grafana; and per-request traces in
[Langfuse/Phoenix] showing every node, retrieved chunks, and LLM call with tokens and latency.
When a request is slow, I open its trace and see which node caused it."

**Follow-up:** "Why p95 not average?" "Averages hide the slow tail that unlucky users feel."

---

### Q7. "Walk me through your Dockerfile choices."

**Model answer:** "Multi-stage: build wheels in one stage, copy them into a slim runtime, so
no compilers ship. Requirements are installed before source is copied for layer caching. A
non-root user. Model files baked in so containers don't download from Hugging Face on start.
CPU-only torch to shrink the image: [n/a] MB before and after. A health check, and a
`.dockerignore` keeping `.env`, git, and data out."

---

### Q8. "How did you deploy for free, and what went wrong?"

**Model answer:** "Oracle Cloud Always Free ARM VM [or fallback], Docker Compose, Caddy for
automatic Let's Encrypt certificates, a DuckDNS subdomain. [Real story, e.g. ports had to be
opened in both the cloud security list and the VM firewall; an image lacked arm64.] Rollback
is redeploying the previous SHA tag."

---

### Q9. "How do you update documents without re-indexing everything?"

**Model answer:** "A manifest of content hashes per document. Unchanged hash: skip. Changed:
delete that document's points by a source filter, re-chunk, re-embed, upsert, bump the
version. Removed documents' points are deleted. Cache versions are bumped so stale answers
are not served. Verified by changing one doc and counting upserts."

---

### Q10. "How would you scale this to 1,000 concurrent users?"

**Model answer:** "First measure where time goes with the load test and traces. Then:
stateless API replicas behind a load balancer (state already lives in Redis, Postgres,
Qdrant); move CPU-heavy reranking to a GPU or a separate service; a Qdrant cluster or managed
Qdrant; a job queue for ingestion; more caching; and paid LLM tiers with higher limits if the
budget allows. My load test showed [n/a] on [VM size], so the first bottleneck was [n/a]."

---

### Q11. "How do you secure the deployment?"

**Model answer:** "No secrets in git or images; keys in env files and GitHub Secrets;
non-root containers; only Caddy exposed; HTTPS; API keys stored as hashes; per-key rate
limits; CORS limited to the UI origin; input size limits; dependency scanning; least-privilege
tools; PII masked in logs; Grafana behind a password; SSH by key only."

---

### Q12. "API keys vs JWT?"

**Model answer:** "API keys suit a few known clients and one service: simple, revocable,
stored as a hash. JWT suits user logins with expiry and many services verifying tokens
without a database lookup. I'd switch when real user accounts arrive."

---

### Q13. "What would you do with more time?"

**Model answer:** "From my stretch list, prioritised by the evals: [e.g. GraphRAG-lite for
multi-hop questions, which were my weakest type at n/a; trajectory evals; DSPy against the
golden set]. And grow the golden and red-team sets from real usage via the review flywheel."

---

### Q14. "Tell me about a negative result."

**Model answer:** "[From your decision log, e.g. 'HyDE did not beat the reranked hybrid
baseline: n/a vs n/a, and it added an LLM call, so I dropped it.'] Negative results told me
where not to spend complexity, and recording them kept me honest."

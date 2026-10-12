# Primer: Model and RAG Monitoring (after deployment)

Used in: Phase 7 step 7.7. Decision: D-022 (MLflow) and the metrics in architecture part 2.

---

## 1. Like I'm five

**Evals** are the **exam** a student takes in class, with an answer key.
**Monitoring** is watching the student at their **real job**, where nobody has an answer
key. You cannot mark every answer right or wrong, but you can watch for **warning signs**:

- "They are saying *I don't know* much more often than last week." (refusal rate up)
- "They are getting questions about subjects they never studied." (topic drift)
- "They are slow today." (latency up)
- "They keep calling the substitute teacher." (LLM fallbacks up)

Monitoring does not prove quality. It tells you **when to look** and **where**.

---

## 2. Why AI systems need special monitoring

Normal web apps fail loudly (errors, crashes). AI systems often fail **quietly**: the server
returns `200 OK` with a confident wrong answer. Reasons it can drift over time:

| Cause | Example |
|---|---|
| Users ask new things | people start asking about Kubernetes, which we never indexed |
| Docs changed | a new FastAPI version renames a parameter; our index is old |
| Provider changed | the free LLM model is updated or replaced; answers change style or quality |
| Our change | a new prompt or retrieval setting that passed evals behaves differently on real traffic |

---

## 3. What we monitor, how, and why

| Signal | How we measure it | Why it matters | Metric (Prometheus) |
|---|---|---|---|
| **Retrieval scores** | top-1 and top-5 rerank (or similarity) score per request, as a histogram | falling scores = questions match our docs less well | `docpilot_retrieval_top_score` (histogram) |
| **Relevant chunks found** | grader's count of relevant chunks per request | many zeros = retrieval failing | `docpilot_relevant_chunks` (histogram) |
| **Groundedness (sampled)** | a background job judges a random ~5% of answers with the judge LLM (faithfulness) | the only quality signal on live traffic; sampled to save free-tier calls | `docpilot_groundedness_sampled` (histogram) |
| **Refusal / abstention rate** | share of answers that are "not found" | sudden rise = retrieval broke or new topics; sudden fall = maybe hallucinating | `docpilot_answers_total{status=...}` |
| **Guard block rate** | blocks by reason | attack wave, or a guard too strict | `docpilot_guard_blocks_total{reason}` |
| **Latency** | p50 / p95 per endpoint and per graph node | user experience; finds the slow node | `docpilot_request_seconds`, `docpilot_node_seconds` |
| **Fallback count** | LLM provider switches | primary provider failing or rate-limiting | `docpilot_llm_fallback_total` |
| **Cache hit rate** | hits / (hits + misses) | cost saving; a jump may mean a bad semantic-cache threshold | `docpilot_cache_hits_total`, `_misses_total` |
| **Review-queue size** | pending human reviews | humans overloaded, or confidence threshold wrong | `docpilot_review_queue_size` (gauge) |
| **Topic drift** | distance between recent questions and our documents (below) | users moving outside what we indexed | `docpilot_topic_drift` (gauge) |

**Cardinality rule (again):** labels have few values (`status`, `reason`, `node`). Never the
question text or a request id.

---

## 4. Topic drift, explained simply

**Like I'm five:** draw a dot on the meaning map for each of our documents; their middle point
is "home". Each day, draw a dot for each user question and find *their* middle point. If the
questions' middle point walks away from home, users are asking about other things.

**Two simple measures (computed by a small scheduled job, `observability/drift_job.py`):**

1. **Centroid distance:** average embedding of last N questions vs average embedding of our
   chunks; report `1 - cosine` between them. Rising = drift.
2. **Out-of-scope share:** share of recent questions whose best retrieval score is below a
   threshold (or that the topic guard flagged). Easier to explain; often more useful.

The threshold values are chosen from real data after launch, not guessed now.
Questions are embedded and **then discarded**; we store numbers, not user text (privacy).

---

## 5. Sampled groundedness, explained simply

Judging every answer would spend the free LLM quota. So a background job picks about 1 in 20
answers at random, asks the judge LLM "is each claim supported by the retrieved chunks?",
and records the score. Random sampling keeps it fair; the sample rate is a setting. Answers
are taken from the trace/log store with PII already masked.

---

## 6. Alerts: when to wake up

Starting rules (thresholds set after one week of real traffic, never invented now):

| Alert | Fires when |
|---|---|
| High error rate | 5xx share above X% for 10 minutes |
| Latency | p95 above Y seconds for 15 minutes |
| Refusal spike | refusal rate doubles vs the 7-day average |
| Groundedness drop | sampled groundedness 7-day average falls below the eval baseline minus tolerance |
| Fallback storm | more than Z fallbacks in 10 minutes |
| Review backlog | queue size above Q for an hour |

Grafana alerting (or Prometheus Alertmanager, VERIFY) sends an email. CloudWatch alarms cover
the machine itself (see `primer_aws.md`).

---

## 7. The Grafana dashboard layout

```text
Row 1  Traffic:   requests/min | error rate | p50/p95 latency
Row 2  Quality:   retrieval top score (heatmap) | sampled groundedness | refusal rate
Row 3  Safety:    guard blocks by reason | review queue size
Row 4  Cost:      LLM calls by provider | fallbacks | cache hit rate
Row 5  Drift:     topic drift | out-of-scope share
```

---

## 8. Closing the loop

Monitoring finds a problem -> you read traces of affected requests -> you add those questions
to the golden set (after human review) -> you fix -> the **offline eval** proves the fix ->
the CI gate protects it from coming back. Monitoring and evals are two halves of one loop.

---

## 9. Self-check

1. Exam vs real job: how do evals and monitoring differ?
2. Why do AI systems fail "quietly"?
3. Name six signals we monitor and why each matters.
4. Explain topic drift with the meaning-map dots.
5. Why is groundedness only sampled?
6. Why are alert thresholds set after launch, not now?

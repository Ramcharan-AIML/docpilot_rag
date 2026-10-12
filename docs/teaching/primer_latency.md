# Primer: Latency (before and after deployment)

Used in: Phase 1 (baseline L0, step 1a.8 onward), Phase 3 (reranker cost), Phase 4
(agents), Phase 6 (guard cost), Phase 7 (streaming, load test, monitoring).
Decision: D-031.

---

## 1. Like I'm five

You order food in a restaurant.

- **Latency** = the time from ordering until the food is on your table.
- **Time to first token (TTFT)** = the time until the **first bite** arrives. If the
  starter comes fast, waiting for the main course feels shorter, even if the total is the
  same. That is why chat apps **stream** words one by one.
- **Per-stage time** = how long the waiter took, how long the kitchen took, how long the
  food sat at the pass. If dinner is slow, you need to know **which stage** is slow
  before you can fix anything.
- **Throughput** = how many tables the restaurant serves per hour. A restaurant can be fast
  for one table and slow when 50 tables order at once.

---

## 2. The words, precisely

| Word | Meaning | DocPilot example |
|---|---|---|
| Latency | time for one request, start to finish | `03_ask.py` question to printed answer |
| Per-stage latency | time of each step inside the request | embed query, search, LLM |
| p50 (median) | half of requests are faster than this | "typical" user experience |
| p95 | 95% of requests are faster; 5% are slower | the unlucky user; what alerts watch |
| p99 | 99% faster | the very slow tail; needs many requests to measure |
| Tail latency | the slow end (p95, p99) | rate-limit retries, cold starts |
| Cold vs warm | first call (load model, open connection) vs later calls | first `get_model()` is slow, later ones are instant |
| TTFT | time until the first token of the answer arrives | matters once we stream (Phase 7) |
| Tokens per second | how fast the LLM writes after it starts | provider and model dependent |
| Throughput | requests handled per second | measured in the Phase 7 load test |
| Latency budget / SLO | the target, e.g. "p95 under N seconds" | set **after** we measure L0, never guessed |

**Why p95 and not the average?** Averages hide the slow tail. Made-up example (teaching
only, not a DocPilot number): nine requests at 1 s and one at 11 s. Average = 2 s, which
nobody actually experienced. p50 = 1 s, and the slow one shows up in p95/p99. One in
twenty users waiting a long time is a real problem the average hides.

---

## 3. Where the time goes in a RAG request

```text
question
  -> embed query      local CPU model (BGE-small): small, fast after warm-up
  -> vector search    Qdrant: fast for thousands of chunks
  -> (rerank)         Phase 3: cross-encoder on CPU, can be the slowest local step
  -> LLM call         network + provider queue + reasoning tokens + answer tokens
  -> answer
```

In most RAG systems the **LLM call dominates**. Our model (gpt-oss-120b) is a reasoning
model: it "thinks" before answering, and those hidden tokens take time too. Measure it;
do not assume it.

**Before deployment** (on the laptop) we measure the code. **After deployment** new
costs appear: network between user and server, the server's smaller CPU, many users at
once (queueing), cold starts after a restart, and free-tier rate limits (429 → retry →
long tail).

---

## 4. How to measure honestly (rules from D-031)

1. Use `time.perf_counter()` (a stopwatch for durations), not `time.time()` (a wall clock
   that can jump).
2. Time **each stage** and the **total**.
3. **Warm up first**, then measure. Report cold start separately; it is real, but it is a
   different number.
4. Report **n**. "p95 over 5 questions" is almost meaningless; say so.
5. **Name the hardware and provider:** "laptop CPU, Groq gpt-oss-120b, free plan".
6. Never compare latency from different machines or providers as if they were the same.
7. Never invent a target. Measure L0, then decide a budget.

```python
import statistics
import time

start = time.perf_counter()
...  # the work
elapsed_ms = (time.perf_counter() - start) * 1000

# p50 and p95 from a list of measurements (needs a reasonable n)
p50 = statistics.median(times_ms)
p95 = statistics.quantiles(times_ms, n=20)[18]  # the 19th of 19 cut points = 95th percentile
```

---

## 5. When we measure what (the plan)

| Phase | What | Output |
|---|---|---|
| 1 (1a.8, 1d) | per-stage timings in `ask()`; p50/p95 over the dev questions | baseline **L0** next to C0 |
| 3 | reranker candidates 20/30/50, embedding models | quality vs latency table (C7) |
| 4 | agentic vs plain RAG | extra LLM calls and p95 per question type |
| 6 | guard overhead | added p50 per guard set |
| 7 before deploy | streaming: TTFT vs total; load test (Locust/k6) | p50/p95/error rate at N users |
| 7 after deploy | Prometheus histograms, Grafana p95 panel, alert on p95 | live latency with instance type named |

---

## 6. Ways to make it faster (each one measured, never assumed)

| Lever | Helps | Costs |
|---|---|---|
| Streaming | perceived latency (TTFT) | total time unchanged; harder error handling |
| Cache answers or embeddings | repeat questions become instant | stale answers if docs change |
| Fewer LLM calls (skip agent loop for simple questions) | big | may lower quality on hard questions |
| Smaller or non-reasoning model | big on the LLM stage | quality: check faithfulness |
| Fewer rerank candidates | rerank stage | recall may drop |
| Shorter context (top-k, chunk size) | fewer input tokens | may miss the answer |
| Warm start (load model at server start) | removes cold start for users | slower boot |

---

## 7. Interview questions

**Q: "How fast is your system?"**
Answer with stage, statistic, n and hardware: "On my laptop CPU with Groq gpt-oss-120b,
p50 was [n/a] s and p95 [n/a] s over [n/a] dev questions. The LLM stage was most of it.
Retrieval was [n/a] ms." Never say "fast".

**Q: "Why p95 and not average?"**
"Averages hide the slow tail; one user in twenty waiting a long time is a real problem."

**Q: "Your reranker improved quality. What did it cost?"**
"[n/a] ms at p95 on CPU for 30 candidates; I chose [n] candidates from the quality vs
latency table."

**Q: "Latency in production was worse than on your laptop. Why?"**
"Network, a smaller CPU, concurrent users, cold starts, and rate-limit retries on the free
tier. That is why I load-tested before going live and alert on p95, not on the average."

**Q: "How would you reduce latency?"**
"First find the slow stage from per-stage timings, then pick the lever for that stage:
streaming for perceived speed, caching for repeats, fewer LLM calls for simple questions,
and measure quality after each change."

---

## 8. Common mistakes

- Measuring once and calling it "the latency".
- Including the model download or first load in a warm number.
- Reporting averages only.
- Comparing a laptop number with a cloud number.
- Optimising the vector search when the LLM takes most of the time.
- Making it faster and not re-checking quality (a fast wrong answer is still wrong).

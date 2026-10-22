# Primer: Prometheus and Grafana (monitoring, from zero)

Simple English. Read this before we build monitoring for DocPilot (Phase 7).

---

## 1. The problem: you cannot see inside a running app

On your laptop you run a script and read the numbers it prints. In production the app runs
all day, for many users, on a server you do not watch. You still need to know:

- Is it fast? (How long do answers take right now?)
- Is it healthy? (Are there errors?)
- Is it doing its job? (How often does it say "I could not find this"?)

**Monitoring** answers these questions all the time, with live charts and alarms.

---

## 2. The two tools in one picture

| Tool | Like I'm five | Real job |
|---|---|---|
| **Prometheus** | A robot with a notebook. Every 15 seconds it visits your app, reads its numbers, and writes them down with the time. | Collects and stores **metrics** (numbers over time). |
| **Grafana** | A TV screen. It reads the robot's notebook and draws charts. | Dashboards and alerts. |
| **`/metrics` page** | A notice board on your app where it writes its current numbers. | The page Prometheus reads. |

```
 You (browser) ──▶ Grafana     http://localhost:3000    draws the charts
                     │  asks: "p95 time of the last 5 minutes?"
                     ▼
                  Prometheus  http://localhost:9090    stores the numbers
                     │  every 15 s: "give me your numbers"   (this is called scraping)
                     ▼
                  DocPilot API http://127.0.0.1:8000/metrics   the notice board
                     ▲
                     │  every question updates the numbers
                  Users asking questions
```

**Important:** Prometheus **pulls** (it goes to the app). The app does not send anything.
If the app dies, Prometheus notices at once: the visit fails.

---

## 3. Metrics vs logs

| | Log | Metric |
|---|---|---|
| What | One sentence per event: "question 123 took 2.7 s" | A number tracked over time: "answers in the last 5 min: p95 = 3.1 s" |
| Good for | Finding out what happened to ONE request | Seeing trends, drawing charts, firing alarms |
| Size | Grows with every request | Small: a few numbers per scrape |

Real teams use both. Prometheus is for metrics.

---

## 4. The three kinds of metrics we use

| Kind | Simple meaning | DocPilot examples |
|---|---|---|
| **Counter** | A number that only goes up (like a car's total kilometres). | Total questions. Total "not found" answers. Total errors. |
| **Gauge** | A number that goes up and down (like a speedometer). | Requests being answered right now. |
| **Histogram** | Puts each measurement into time "buckets" and counts them. | Time per stage: embed, search, rerank, LLM, total. |

**How a histogram works (example):** we have buckets "under 0.1 s", "under 0.5 s",
"under 1 s", "under 2.5 s", "under 5 s". A question that takes 0.8 s adds 1 to every
bucket from "under 1 s" upward. From these counts Prometheus can **estimate** p50 and p95.

---

## 5. Latency in production: p50 and p95

- **p50** (median): half of the requests are faster than this. "The normal user."
- **p95**: 95% are faster than this. "The unlucky 1 user in 20."
- Why p95 matters: the average hides the slow requests; users remember the slow ones.

**Two differences from our evals:**
1. Our evals sorted an exact list of times. Prometheus **estimates** from bucket counts.
2. Prometheus looks at a **moving window** (for example "the last 5 minutes"), so the chart
   changes when traffic changes.

**What we expect to see in DocPilot (from our evals, laptop):** search is tiny (about
12 ms), the reranker is about 0.5 s, the LLM is about 1 s. With several users at the same
time, requests wait for the CPU, so p95 grows. The load test will show this live.

---

## 6. PromQL: the question language (only 3 lines to know)

You type these in Prometheus (http://localhost:9090) or Grafana.

```text
rate(docpilot_requests_total[5m])
```
How many questions per second, averaged over the last 5 minutes.

```text
histogram_quantile(0.95, sum by (le) (rate(docpilot_stage_seconds_bucket{stage="total"}[5m])))
```
p95 total answer time over the last 5 minutes. (`le` = "less or equal", the bucket edge.)

```text
rate(docpilot_not_found_total[5m]) / rate(docpilot_requests_total[5m])
```
Refusal rate: the share of questions answered with "I could not find this".

(The metric names are the ones we will create; the exact names are fixed when we build.)

---

## 7. Where to download them? You do not.

Both come as **official Docker images**: `prom/prometheus` and `grafana/grafana`. We add
them to `docker-compose.yml` (with an exact version, never "latest") and run:

```powershell
docker compose up -d
```

Docker downloads them from Docker Hub the first time, like Qdrant, SeaweedFS and MLflow.

**Why Docker and not a Windows installer?** The same compose file then runs unchanged on
the AWS server. A Windows install works only on your PC.

---

## 8. Where to look

| Address | What you see |
|---|---|
| http://127.0.0.1:8000/metrics | Our app's raw numbers, plain text |
| http://localhost:9090 | Prometheus. Menu **Status > Targets**: is our app "UP"? Also a box to type PromQL |
| http://localhost:3000 | Grafana. Log in, open the DocPilot dashboard |

---

## 9. How we build it (the steps)

| Step | What | What you learn |
|---|---|---|
| 1 | Add the `prometheus-client` library; the API gets a `/metrics` page; `ask()` records the time of every stage | How an app "exposes" metrics |
| 2 | `monitoring/prometheus.yml`: where the app is, how often to visit | Scraping |
| 3 | Prometheus + Grafana in `docker-compose.yml` (pinned versions, named volumes) | Monitoring in Docker |
| 4 | Grafana files that create the data source and the dashboard automatically | Dashboards as code (no clicking) |
| 5 | Start the API, send questions with a small load test, watch the charts | Latency under several users |
| 6 | Later: the API goes into Docker too, and everything runs on AWS | Production |

**A Windows detail:** while the API runs on your PC (not in Docker), Prometheus (inside
Docker) reaches it at `host.docker.internal:8000`. That name means "the PC that runs
Docker". Once the API is a container, it is reached by its service name instead.

**Saving LLM quota:** every real question calls the LLM (free-tier limits). The load test
stays small, and a "search only" mode tests search + reranker without any LLM call.

---

## 10. Why these tools and not others?

| Alternative | Why not for us |
|---|---|
| Paid monitoring (Datadog, New Relic) | Costs money; our rule is free only |
| AWS CloudWatch only | Works only on AWS; Prometheus + Grafana work on the laptop, AWS and Oracle the same way |
| Only logs | No charts over time, no p95 per 5 minutes, hard to alarm on |
| MLflow | Built for experiments (one run = one result), not for live traffic every 15 seconds |

---

## 11. Interview answers in one breath

- "Prometheus **pulls** metrics from a `/metrics` endpoint every few seconds and stores them
  as time series; Grafana queries Prometheus with PromQL and draws dashboards."
- "I track latency **per stage** with histograms, so I can see that the LLM and the
  reranker, not the vector search, drive p95."
- "p95 from a histogram is an **estimate over a time window**; offline eval p95 is exact over
  a fixed set. They answer different questions."
- "I also track the refusal rate: a sudden rise can mean the index is broken or users ask
  about new topics."

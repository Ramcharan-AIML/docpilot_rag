# Phase 7: Production (Implementation Plan, Part 1 of 2)

**Goal of the phase:** turn the working system into a service that strangers can use
safely: hardened API, auth, rate limits, caching, provider fallbacks, tracing, metrics,
containers, CI/CD with an eval gate, and a public HTTPS URL on a free VM.

**Teaching companion:** `docs/teaching/phase_7_production.md` and `2_phase_7_production.md`
**Part 2:** `2_phase_7_production.md` (Docker image, Compose, CI/CD, deploy, load test, README)

Part 1 covers the **application** side: 7.1 to 7.6.

---

## Step 7.1: FastAPI hardening

**Folder:** `src/docpilot/api/` (started in Phase 5)

| File | Contents |
|---|---|
| `app.py` | `create_app()` factory; lifespan opens Qdrant, Redis, Postgres pools, loads models once |
| `schemas.py` | `AskRequest`, `AskResponse(answer, citations, confidence, status, request_id)`, `ErrorResponse` |
| `middleware.py` | request id (from `X-Request-ID` or new UUID), timing, JSON access log |
| `routes_ask.py` | `POST /ask`, `POST /ask/stream` |
| `routes_health.py` | `GET /health` (alive), `GET /ready` (dependencies reachable), `GET /metrics` |
| `errors.py` | exception handlers: never leak stack traces to users; always return `request_id` |

### 7.1.1 Async: what changes

- Endpoints become `async def`. Network calls (LLM, Qdrant, Redis, Postgres) use async
  clients where the library offers them (VERIFY each).
- CPU-heavy work (embedding, reranking) must **not** run on the event loop: wrap it with
  `await asyncio.to_thread(...)` (or `run_in_threadpool`), otherwise one rerank blocks every
  other request.
- Every outgoing call has a timeout (`asyncio.timeout` / client timeout settings).

### 7.1.2 Streaming with Server-Sent Events

```python
# routes_ask.py (sketch)   VERIFY: StreamingResponse / SSE helper in current FastAPI
async def token_stream(question: str):
    async for event in run_graph_streaming(question):     # graph yields tokens + final meta
        # SSE format: "data: <text>\n\n" for each message
        yield f"data: {json.dumps(event)}\n\n"


@router.post("/ask/stream")
async def ask_stream(request: AskRequest):
    return StreamingResponse(token_stream(request.question), media_type="text/event-stream")
```

Rule: output guards need the **whole** answer. So we stream progress events (`retrieving`,
`grading`, `generating`) and the final checked answer, or we stream tokens and send a
final `guard` event that can retract them. Decide, measure perceived latency, log the
decision. (Streaming unchecked tokens and checking afterwards is a known trap.)

### 7.1.3 Structured logs

`src/docpilot/observability/logging.py`: one JSON object per line to stdout:
`timestamp, level, request_id, event, node, ms, status`. No raw question text unless
PII-masked. Docker collects stdout, so no log files inside containers.

---

## Step 7.2: Authentication with API keys

**Files:** `api/auth.py`, `scripts/07_create_api_key.py`, Postgres table `api_keys`

```python
"""API key check. We store only a hash, like passwords."""
import hashlib

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_key(raw_key: str) -> str:
    # Keys are long random strings (made by secrets.token_urlsafe(32)), so a fast hash is
    # enough. Short human passwords would need a slow hash such as bcrypt instead.
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def require_api_key(raw_key: str | None = Security(api_key_header)) -> str:
    if not raw_key:
        raise HTTPException(status_code=401, detail="missing API key")
    # Look up by hash: the database never holds the raw key, so a leaked
    # database dump does not leak usable keys.
    key_record = await find_key_by_hash(hash_key(raw_key))    # Postgres lookup
    if key_record is None or key_record.revoked:
        raise HTTPException(status_code=401, detail="invalid API key")
    return key_record.key_id                                  # used for rate limits and logs
```

Why API keys and not JWT for now: one deployment, a few users, no login flow. JWT adds
signing keys, expiry, refresh. Record "switch to JWT/OAuth when there are real user
accounts" in `decisions.md`.

**Postgres arrives** here in Compose (it also stores LangGraph checkpoints and the review
queue, replacing SQLite). VERIFY the LangGraph Postgres checkpointer package.

---

## Step 7.3: Redis: rate limiting and caching

**Files:** `api/rate_limit.py`, `cache/exact_cache.py`, `cache/semantic_cache.py`

### 7.3.1 Rate limiting (raw first)

```python
"""Fixed-window rate limit: at most N requests per key per minute."""
import time

REQUESTS_PER_MINUTE = 20   # starting value; tune to the LLM free-tier limits


async def allow_request(redis, key_id: str) -> bool:
    window = int(time.time() // 60)                  # current minute number
    counter_key = f"ratelimit:{key_id}:{window}"
    count = await redis.incr(counter_key)            # atomic: safe with many workers
    if count == 1:
        await redis.expire(counter_key, 70)          # old windows delete themselves
    return count <= REQUESTS_PER_MINUTE
```

Return `429` with a `Retry-After` header when over. Teaching note: fixed windows allow a
burst at the boundary (20 at 0:59 and 20 at 1:00); a sliding window or token bucket fixes
it. Mention it; implement only if load tests show it matters.

### 7.3.2 Exact cache

Key: `sha256(normalised question + retrieval settings version + prompt version + model)`.
Why include versions: after a prompt change, old cached answers must not be served.
TTL: 24 hours (setting). Only cache `answered` results that passed output guards; never
cache `pending_review` or `blocked`.

### 7.3.3 Semantic cache (and its danger)

- Embed the question; find the nearest cached question; reuse if cosine >= threshold.
- VERIFY whether our Redis version supports vector search. If not, store cache vectors in a
  small Qdrant collection `semantic_cache` and answers in Redis. Decision entry either way.
- **Danger:** "How do I make a query parameter optional?" and "...required?" are very
  close in meaning but have opposite answers. A wrong hit serves a wrong answer.
- **Test set:** `evals/cache/near_miss_pairs.jsonl`: pairs that must NOT share an answer,
  and paraphrase pairs that SHOULD. Report false-hit rate and true-hit rate per threshold.
  Pick the threshold from the data. If no threshold gives a near-zero false-hit rate, ship
  without the semantic cache and say so. That is a mature engineering decision.

---

## Step 7.4: LLM gateway with fallbacks

### 7.4.1 Hand-written first: `llm/fallback.py`

```python
"""Try providers in order; skip ones that recently rate-limited us."""
import time

COOLDOWN_SECONDS = 60
_cooldown_until: dict[str, float] = {}     # provider -> time when it may be tried again


def complete_with_fallback(providers: list[str], system: str, user: str) -> tuple[str, str]:
    errors = []
    for provider in providers:
        if time.time() < _cooldown_until.get(provider, 0):
            continue                                       # still cooling down
        try:
            client = get_llm_client(provider)
            return chat(client, system, user), provider    # answer + who answered (for metrics)
        except RateLimitError:
            _cooldown_until[provider] = time.time() + COOLDOWN_SECONDS
            errors.append(f"{provider}: rate limited")
        except (TimeoutError, APIError) as error:
            errors.append(f"{provider}: {error}")
    raise AllProvidersFailed("; ".join(errors))
```

Note: `_cooldown_until` lives in one process. With several workers each has its own copy.
That is acceptable for a cooldown (worst case: one extra failed try); move it to Redis if
metrics show it matters.

### 7.4.2 Then LiteLLM: `llm/gateway.py`

- VERIFY: current Router / fallback configuration syntax, model naming per provider.
- Same order: Groq -> Gemini -> OpenRouter free -> Ollama. Retries with backoff.
- Test: put a fake bad key for Groq in a test `.env`; prove the answer arrives from the
  next provider and the `fallback_total` metric increments.
- Keep the `LLMClient` protocol: the agents do not know which one is used.

---

## Step 7.5: Tracing (decide D-009)

1. VERIFY current state of Langfuse (cloud free tier limits; self-host requirements) and
   Arize Phoenix (self-host footprint). Check RAM on the target VM.
2. Write a two-option comparison in `decisions.md`, choose, close D-009.
3. **File:** `observability/tracing.py`: a thin wrapper `start_trace(request_id)`,
   `span(name)`, so the tracing tool can be swapped.
4. Each request trace shows: guard decisions, route, retrieved chunk ids and scores, grades,
   rewrites, LLM calls with provider, tokens, latency per node.

**Done when:** you can open one slow request's trace and say which node made it slow.

---

## Step 7.6: Metrics and dashboards

**File:** `observability/metrics.py` using `prometheus_client` (VERIFY version)

| Metric | Type | Labels |
|---|---|---|
| `docpilot_requests_total` | Counter | endpoint, status |
| `docpilot_request_seconds` | Histogram | endpoint |
| `docpilot_node_seconds` | Histogram | node |
| `docpilot_llm_calls_total` | Counter | provider, purpose (grade, generate...) |
| `docpilot_llm_fallback_total` | Counter | from_provider, to_provider |
| `docpilot_cache_hits_total` / `_misses_total` | Counter | cache (exact, semantic) |
| `docpilot_guard_blocks_total` | Counter | reason |
| `docpilot_review_queue_size` | Gauge | n/a |

Rule: labels must have few possible values. Never put `request_id` or the question in a
label (it would create millions of series and crash Prometheus).

**Files:** `deploy/prometheus.yml` (scrape `api:8000/metrics` every 15 s),
`deploy/grafana/dashboards/docpilot.json`, `deploy/grafana/provisioning/` (datasource and
dashboard auto-loaded at start).

Dashboard panels: requests per minute, error rate, p50/p95 latency, latency per node,
cache hit rate, fallback count, guard blocks by reason, review queue size.

Continued in [2_phase_7_production.md](2_phase_7_production.md)

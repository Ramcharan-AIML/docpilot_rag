# Teaching Notes, Phase 7: Production (Part 1 of 2)

Plan files: `docs/implementation_plan/phase_7_production.md`, `2_phase_7_production.md`

Part 1: what "production" means, async APIs, streaming, auth, rate limiting, caching,
LLM gateways. Part 2: observability, Docker images, Compose, CI/CD, cloud, HTTPS, load
testing, incremental ingestion.

---

## 1. What "production" means

**Like I'm five:** cooking for your family vs running a restaurant. At home, if dinner is
late or one dish fails, nobody sues. A restaurant needs a door policy, a booking limit,
hygiene rules, a fridge for leftovers, a backup supplier, cameras, and an inspection.

| Home cooking (notebook) | Restaurant (production) |
|---|---|
| Runs when you press play | Runs 24/7, restarts itself |
| You are the only user | Strangers, some hostile |
| Errors print on your screen | Errors are logged, counted, alerted |
| "Works on my machine" | Same container everywhere |
| You check quality by eye | CI checks it on every change |

---

## 2. Async, properly this time

**Like I'm five:** one waiter, many tables. A **blocking** waiter takes an order, walks to
the kitchen, and **stands there** until the food is ready; every other table waits. An
**async** waiter hands the order in and serves other tables while the kitchen cooks.

**What it really is:** `async def` + `await` lets one Python process handle many requests
that are **waiting on the network** (LLM APIs, Qdrant, Redis) at the same time.

**The trap:** async only helps with **waiting**. CPU-heavy work (embedding, reranking)
keeps the waiter busy with his own hands; nobody else is served. So we push CPU work to a
thread (`asyncio.to_thread`) and keep network calls async.

**Timeouts everywhere:** a hung provider must not hold a request forever. Every outgoing
call has a timeout; the gateway falls back to the next provider.

---

## 3. Streaming with Server-Sent Events (SSE)

**Like I'm five:** a chef who sends each course as soon as it is ready, instead of making
you wait until dessert to get anything.

**What it really is:** the server keeps the HTTP response open and sends small messages
(`data: ...\n\n`) as they are ready. The user sees progress immediately: the **time to
first token** drops, even if total time is the same.

**Why SSE and not WebSockets:** we only need server-to-client messages. SSE is plain HTTP,
simpler, works through proxies. WebSockets are two-way and more complex.

**The RAG-specific trap:** output guards need the **full** answer. If you stream tokens raw,
the user may see an unchecked (possibly leaking) answer before the guard runs. Options:
stream progress events and the final checked answer, or stream tokens and allow a final
"retract" event. Choose, measure, write it down.

---

## 4. Authentication with API keys

**Like I'm five:** a gym membership card. The front desk does not store a copy of your
card; it stores a **fingerprint** of it (a hash), and checks the fingerprint when you
arrive.

- The key is a long random string given to the user once.
- The database stores only `sha256(key)`. A leaked database dump does not leak usable keys.
- Requests send `X-API-Key`; we hash and look it up.
- Long random keys make a fast hash enough. **Human passwords** are short and guessable,
  so they need a slow hash (bcrypt, argon2) instead. Know this difference.

**Why not JWT now:** JWT shines with user logins, expiry, and many services verifying
tokens without a database. We have a few users and one service. API keys are simpler.
Record when you would switch.

**Auth vs authorisation:** authentication = who are you; authorisation = what may you do
(e.g. only reviewers may call `/reviews/*`). We need both for reviewer endpoints.

---

## 5. Rate limiting

**Like I'm five:** a "max 20 rides per hour" stamp on a theme-park wristband.

**Why:** protects our free-tier LLM quota, protects the server, stops abuse.

**Fixed window in Redis:** key `ratelimit:<key_id>:<minute>`, `INCR` it, set expiry on the
first hit, refuse when over the limit. `INCR` is atomic, so many workers can share the
counter safely. **That is why Redis and not a Python dict:** each worker process has its
own dict; limits would multiply by the number of workers and vanish on restart.

**Known weakness:** 20 requests at 0:59 and 20 at 1:00 = 40 in two seconds. Sliding windows
or token buckets smooth this. Good to know; implement if needed.

**Return 429 with `Retry-After`** so polite clients know when to come back.

---

## 6. Caching

**Exact cache:** same question (after normalising) -> same stored answer. The key must also
include versions of the prompt, model, and retrieval settings: after any change, old
answers must not be served.

**Semantic cache:** "nearly the same question" -> reuse. Saves LLM calls on paraphrases.

**The danger, in one example:** "How do I make a query parameter **optional**?" and
"...**required**?" are very close as vectors but have opposite answers. A semantic cache
can confidently serve the wrong one. So we build near-miss pairs, measure false-hit rate
per threshold, and only ship the cache if a threshold gives near-zero false hits.
"I measured it and turned it off" is a strong engineering answer.

**What never gets cached:** blocked requests, pending human reviews, unguarded answers.

---

## 7. LLM gateway and fallbacks

**Like I'm five:** your favourite pizza place is closed, so you call the second, then the
third, and finally cook at home (Ollama). You also remember "place one was closed, don't
call them again for an hour" (cooldown).

**Hand-written first:** a loop over providers with try/except, a cooldown dictionary, and
a record of which provider answered (for metrics). Then **LiteLLM**, which adds a unified
model naming scheme, retries with backoff, and routing, tested against our own version.

**Retries with exponential backoff:** wait 1 s, then 2 s, then 4 s... so you do not hammer
a provider that is already overloaded. Add a little randomness ("jitter") so many clients
do not retry at the same instant.

**Different models answer differently.** A fallback to a weaker model can lower quality.
That is why the provider used is recorded per answer and visible in metrics and traces.

---

## 8. Self-check (part 1)

1. Why does async not speed up embedding? What do we do about it?
2. Why SSE over WebSockets? What is the streaming + guardrails trap?
3. Why store a hash of the API key? Why is sha256 fine for keys but not for passwords?
4. Why must rate-limit counters live in Redis?
5. Give a semantic-cache false hit. How did you choose the threshold?
6. What is a cooldown, and what is exponential backoff with jitter?

Continued in [2_phase_7_production.md](2_phase_7_production.md)

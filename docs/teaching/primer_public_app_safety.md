# Primer: making a laptop app safe for strangers (Stage A, from zero)

Simple English. Written 2026-10-23, before Stage A is built. Real results are added after
each step (never before: no invented numbers).

---

## 1. The big picture

Today DocPilot has ONE user: you, on your laptop. A public link changes 3 things:

| What changes | Danger | Stage A step |
|---|---|---|
| Strangers use it | They see each other's chats | A1 private chats |
| They share ONE Groq quota | One person uses it all up | A2 limits, A4 "busy" |
| They share ONE small server (2 GB) | Too many at once = crash | A3 queue, A5 disk, A6 cleanup, A7 ready |

**Real-life example:** your home kitchen is fine for your family. To open it as a shop
you need private tables (A1), a "max 2 plates per person" rule (A2), a queue at the door
(A3), a "sorry, kitchen busy" sign (A4), a store room (A5), cleaning at night (A6), and an
"OPEN / CLOSED" sign (A7).

---

## 2. A1: who is this visitor? (sessions vs accounts)

### 2.1 The problem

Every chat today sits in one SQLite table. The sidebar shows ALL rows. Put it online and
visitor B opens the site and sees visitor A's chats and files. That is a privacy bug.

### 2.2 Three ways to know "who is asking"

| Way | How | Good | Bad |
|---|---|---|---|
| **Nothing** (today) | everyone is the same | simple | no privacy |
| **Visitor id** (our choice) | browser makes a random id once, keeps it, sends it on every call | no login screen, 30 lines of code | not a password; clearing the browser = chats gone from view |
| **Accounts** (login) | username + password, or "Sign in with Google" | real security | passwords, reset emails, sessions, OAuth: days of work |

**Real-life example:** the visitor id is a **cloakroom ticket**. You get a random number
when you arrive. Show the number, get your coat. No ID card needed. But anyone who
copies your ticket number gets your coat too.

### 2.3 How our visitor id works

```text
1. First visit:  browser -> crypto.randomUUID() -> "3f9c...e1"  -> saved in localStorage
2. Every call:   fetch("/api/chats", headers: { "X-Visitor-Id": "3f9c...e1" })
3. Server:       chats table has an "owner" column
                 new chat  -> owner = the header value
                 list      -> only rows WHERE owner = header
                 open/rename/delete/upload/ask -> if owner differs -> 404
```

| Word | Meaning |
|---|---|
| `localStorage` | a small box of text inside the browser, per website; survives closing the tab |
| `crypto.randomUUID()` | browser function: a random 122-bit id; guessing one is practically impossible |
| HTTP **header** | a label on the envelope of a request, next to the letter (body) |
| `X-Visitor-Id` | our own header name (`X-` = "custom", an old habit; still common) |

### 2.4 Why 404 and not 403?

- **403 Forbidden** says "this chat exists, but it is not yours". That leaks a fact.
- **404 Not Found** says "no such chat". A stranger learns nothing.

GitHub does the same: a private repo you cannot see answers 404, not 403.

### 2.5 Why not X?

| Why not... | Because |
|---|---|
| Cookies | Would also work. A header is easier to see in code and tests, and our UI and API are on the same site anyway. A cookie version is a small change later. |
| IP address as the id | Many people share one IP (college Wi-Fi, mobile networks); one person's IP changes |
| Real login now | Days of work, and the deadline is 2026-10-25. Planned for Stage D. |
| Ask the visitor for a name | Two people type "Ram" and see each other's chats |

### 2.6 Old chats (migration)

A **migration** = changing a database table that already has data. Our `data/app.db`
already has chats with no `owner` column. On start, the server checks the table and runs
`ALTER TABLE chats ADD COLUMN owner ...` once. Old rows get owner `""` (empty), so no
visitor sees them. Safe by default: privacy wins over convenience.

### 2.7 The honest limit (say this in an interview)

> "This is privacy, not security. There is no password. If someone copies your visitor id
> from your browser, they can read your chats. For a public demo with no personal data,
> that is an acceptable trade-off; real accounts are the next step."

---

## 3. A2: limits (rate limiting)

**Rate limit** = "at most N requests per time window, per person".

**Real-life example:** a free water tap in a park. Without a rule, one person fills 50
bottles and the queue behind them gets nothing. Rule: 2 bottles per person per visit.

**Measure first.** Groq's free plan (your console, 2026-10-23) for gpt-oss-120b:
30 requests/min, 1K requests/day, **8K tokens/min, 200K tokens/day**. One answer used
1,149 tokens (median of 5, max 1,272). A follow-up also runs the "rewrite" call: about
2,400 tokens (estimate). So the WORD bucket empties first: 8K / 2.4K = **3 turns a minute
for the whole site**, 200K / 2.4K = 83 a day. The plan's guess (10/min) would have
crashed into Groq's limit.

| Limit | Value (built) | Why |
|---|---|---|
| Per visitor | 3 / minute, 20 / day | one person cannot drain the day |
| Per IP address | 3 / minute, 40 / day | clearing the browser (new visitor id) does not reset it |
| Whole site | 3 / minute, 80 / day | stays under Groq's tokens per minute and per day |
| Uploads | 10 files / day per IP, 3 per chat | indexing costs CPU |
| Pages per file | 300 | 301 pages took 94 s to index (measured) |
| File size | 20 MB | upload time and disk |

- **Fixed window** (our choice): count per minute, reset when the minute changes.
  Simple. Weakness: 10 at 0:59 + 10 at 1:01 = 20 in 2 seconds. Fine for a demo.
- **Sliding window / token bucket**: smoother, a bit more code. Interview word to know.
- **In memory** (raw first): a Python dict. Lost on restart, works for ONE server only.
  **Redis** is the shared, survives-restart version (Stage D).
- Answer code: **429 Too Many Requests**, with a clear message.
- `PUBLIC_MODE=1` only on the server, so your laptop stays unlimited.

---

## 4. A3: concurrency (a queue, not a crash)

**Concurrency** = how many things run at the same time.

20 questions at the same second = 20 reranker runs at once on 2 CPUs and 2 GB RAM. Memory
spikes, the server may be killed (OOM = out of memory).

**Semaphore** = a counter of free seats. `Semaphore(2)`: 2 answers run, the 3rd waits for
a seat. **Real-life example:** a barber shop with 2 chairs and a waiting bench.

Result to measure later: memory stays about flat; extra traffic becomes waiting time.

---

## 5. A4: "busy" instead of an error

Groq's free tier answers **429** when we ask too fast. Our client already retries. If it
still fails, the stream sends a friendly message: "DocPilot is busy right now. Please try
again in a minute." A user should never see a stack trace or a spinning wheel forever.

---

## 6. A5: vectors on disk

RAM is small (2 GB) and disk is bigger (20 GB). Qdrant can keep a collection's vectors on
disk and **memory-map** them (the operating system loads only the parts in use).
Uploads go on disk (they grow with every visitor); the small main library stays in RAM
(fast). Exact settings: VERIFY for qdrant-client 1.19.1 on the day.

---

## 7. A6: cleanup

A public demo collects junk forever. Every hour, a background thread deletes chats idle for
more than 7 days: rows, uploaded files, vectors. Same code as the "delete chat" button.

---

## 8. A7: health vs readiness

| Endpoint | Question it answers | Real-life example |
|---|---|---|
| `/health` | "Is the process alive?" | the shop lights are on |
| `/ready` | "Can it answer a question now?" (models loaded, Qdrant reachable, library present) | the cook is in and the fridge is full |

Docker restarts a dead process (health). A monitor like UptimeRobot checks readiness.
Kubernetes uses the same two ideas: liveness and readiness probes.

---

## 9. Interview questions

**Q1. How do you keep users' chats private without a login?**
A random visitor id made in the browser, kept in localStorage, sent as a header. The server
stores it as the chat owner and filters every query by it. Other visitors get 404.

**Q2. Why 404 instead of 403 for someone else's chat?**
403 confirms the chat exists. 404 reveals nothing.

**Q3. What is the weakness of the visitor id?**
It is a bearer token with no password: whoever has it is "you". Fine for a demo with no
personal data; real accounts for anything sensitive.

**Q4. Fixed window vs token bucket rate limiting?**
Fixed window counts per clock minute (simple, allows bursts at the edge). Token bucket
refills tokens at a steady rate (smooth). In-memory works for one server; Redis for many.

**Q5. Why a semaphore?**
To cap work running at once, so memory stays bounded; extra requests wait instead of
crashing the server.

**Q6. Health vs readiness?**
Health = alive (restart if not). Ready = able to serve (send traffic only if yes).

---

## 10. Real results (filled after each step)

| Step | Result | Date |
|---|---|---|
| A2 | Limits set from MEASURED tokens (1,149 median per answer, n=5); unit tests only, live check skipped | 2026-10-23 |
| A3+A4 | 2 seats; full queue shows "Waiting in line" then the busy message; a fake Groq 429 shows the busy message and frees the seat; unit tests only | 2026-10-23 |
| A1 | Normal window and Incognito = two visitors, each sees only their own chats; old chats (owner "") hidden from both. Learner predicted Incognito would share chats (wrong). Gotcha: the first test hit an old server started before the change; restart fixed it. | 2026-10-23 |

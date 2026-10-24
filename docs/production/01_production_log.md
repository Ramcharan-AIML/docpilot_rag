# Production log: DocPilot goes live (Phase 7)

My tracking file for the production work. One section per step, newest step at the
BOTTOM (read it like a story). Each step says: what problem, the simple picture, what we
built, real results, and the important commands.

- Plan (the full map): `docs/implementation_plan/5_phase_7_live_link.md`
- Teaching notes: `02_teach_public_app_safety.md` (Stage A), `03_teach_docker_images.md` (Stage B)
- Rule: ALL production teaching, interview notes and logs live in this folder only
- Decisions: D-062 (hosting), D-063 (public-mode safety) in `docs/3_decisions.md`
- Not listed here on purpose: `git add`, `git commit`, `git push` (I run those myself)

---

## The flow of production (where we are)

```text
Stage A  make the app safe for strangers   (laptop, no AWS)      <- we are here
Stage B  put it in containers + monitoring (laptop, no AWS)
Stage C  go live on AWS (EC2 t3.small, HTTPS, a real link)
Stage D  after submission: logins, Redis, Kubernetes, Oracle move
```

**Why Stage A first:** today the app is built for ONE user (me) on my laptop. A public link
means strangers, ONE shared Groq quota, and ONE small 2 GB server. It is like opening my
home kitchen as a shop: I need private tables, a "max plates per person" rule, a queue at
the door, a "kitchen busy" sign, a store room, night cleaning, and an OPEN/CLOSED sign.

| Step | Kitchen-shop picture | Status |
|---|---|---|
| A1 private chats | private tables | done, checked live |
| A2 limits | max plates per person | built, unit tests |
| A3 queue | 2 chairs + a waiting bench | built, unit tests |
| A4 busy message | "kitchen busy" sign | built, unit tests |
| A5 uploads on disk | the store room | built, checked on Docker Qdrant |
| A6 cleanup | cleaning at night | built, unit tests |
| A7 ready check | OPEN / CLOSED sign | done, checked live |
| B1-B2 Docker image | the packed lunch box | done: 1.86 GB, offline + no-.env checks pass |
| B3 prod stack + Caddy | the shop's front door with a lock | done, ran on the laptop (see `2_production_log.md`) |
| B4 onwards | | logged in `2_production_log.md` |

---

## Step 0: set-up (2026-10-23)

**What happened:**
- PR #6 (the React chat app) was merged into `main` after CI went green.
- A new branch `production` was made for all Phase 7 work.
- I decided my personal notes (interview, teaching, progress, decisions, ...) will be
  removed from GitHub later, before I share the repo link. The `.gitignore` lines are
  written but turned off with `#` for now.

**Important commands:**
```powershell
gh pr checks 6 --watch          # wait until CI (tests, eval gate, GitGuardian) is green
gh pr merge 6 --merge           # merge the PR into main
git checkout main ; git pull ; git checkout -b production ; git push -u origin production
```

**Lesson:** `.gitignore` is a "do not enter" sign: it stops NEW files only. Files git
already tracks need `git rm -r --cached <path>` once (the files stay on my laptop).

---

## Step A1: private chats per visitor (2026-10-23) - DONE, checked live

**Problem:** every chat was in one table and the sidebar showed ALL of them. Online,
visitor B would see visitor A's chats and files.

**Simple picture: a cloakroom ticket.** When you arrive, you get a random ticket number.
Show the number, get your coat. No ID card needed. But anyone who copies your number gets
your coat too.

**How it works:**
```text
1. First visit:  the browser makes a random id (crypto.randomUUID) -> saved in localStorage
2. Every call:   the browser sends it in a header:  X-Visitor-Id: 6df0d430-...
3. Server:       chats table has an "owner" column
                 new chat -> owner = that id
                 sidebar  -> only my chats
                 someone else's chat -> 404 "not found"
```

**What we built:**
| File | Change |
|---|---|
| `src/docpilot/chat/store.py` | `owner` column; old databases get it added on start (a **migration**) |
| `src/docpilot/chat_api.py` | every chat endpoint checks the header; others' chats = 404; bad id = 400 |
| `web/src/api.js` | makes the id once, sends it on EVERY call through one `call()` helper |
| tests | visitor B tries list, open, rename, delete, upload, ask: all fail |

**Small words:**
- `localStorage` = a small box of text inside the browser, per website; survives closing the tab.
- HTTP **header** = a label on the envelope of a request, next to the letter (body).
- **Migration** = changing a table that already has data (`ALTER TABLE ... ADD COLUMN`).

**Why 404 and not 403?** 403 says "it exists, but it's not yours" (that leaks a fact).
404 says "no such chat". GitHub does the same for private repos.

**Why not:** cookies (would work; a header is easier to test), IP address (many people
share one), real login (days of work, later in Stage D).

**Honest limit:** this is privacy, not security. There is no password.

**My check (live):**
- My predictions: Incognito shows the same chats (WRONG: Incognito has its own empty
  localStorage, so it is a new visitor); clearing site data = chats gone (RIGHT: gone from
  my view; the rows stay in the database).
- First try showed the same 3 old chats in both windows. Cause: an OLD server (started
  11:00, before the change) was still running on port 8000. After a restart: two separate
  visitors, old chats hidden. PASS.
- **Lesson:** after changing Python code, restart the server. It loads code once at start.

**Important commands:**
```powershell
uvicorn docpilot.api:app                       # run the app -> http://127.0.0.1:8000
cd web ; npm run build ; cd ..                 # rebuild the React app after UI changes
```
F12 -> Network -> click an `/api/chats` call -> see the `X-Visitor-Id` header.

---

## Step A2: abuse limits (2026-10-23) - built, unit tests (live check skipped)

**Problem:** all visitors share ONE free Groq quota. One person (or a script) could use it
all up, and the site would break for everyone.

**Simple picture: a free water tap in a park.** Without a rule, one person fills 50
bottles and the queue behind gets nothing. Rule: 3 bottles per person per minute.

**Measure first (the big lesson of this step):**
- Groq free limits for our model (my console): 30 requests/min, 1,000 requests/day,
  **8,000 tokens/min, 200,000 tokens/day**. Two buckets: "how many times" and "how many
  words". The WORD bucket empties first.
- I measured one answer: **1,149 tokens** (median of 5, max 1,272).
- A follow-up question also runs a "rewrite" call: about 2,400 tokens per turn (estimate).
- So: 8,000 / 2,400 = **3 turns a minute for the whole site**; 200,000 / 2,400 = 83 a day.
- The old plan said 10 questions/min. That would have been 3x over Groq's limit.

**Limits we chose:**
| Who | Limit | Why |
|---|---|---|
| Each visitor | 3 / minute, 20 / day | one person cannot take the whole day |
| Each IP address | 3 / minute, 40 / day | clearing the browser (new id) does not reset it |
| Whole site | 3 / minute, 80 / day | stays under Groq's limits |
| Uploads | 3 files per chat, 10 per day per IP, 300 pages, 20 MB | indexing costs CPU |

**What we built:**
| File | Change |
|---|---|
| `src/docpilot/limits.py` (new) | a **fixed-window counter** in a Python dict, with a lock |
| `src/docpilot/config.py` | `PUBLIC_MODE=1` turns limits on (server only; laptop unlimited) |
| `chat_api.py`, `api.py` | over the limit = **429 Too Many Requests** + a clear message |
| `scripts/measure_tokens.py` (new) | asks 5 real questions and prints Groq's token counts |

**Small words:**
- **Rate limit** = at most N requests per time window, per person.
- **Fixed window** = count per clock minute, reset when the minute changes. Simple; allows
  a burst at the edge (3 at 0:59 + 3 at 1:01). **Token bucket** = smoother (interview word).
- **In memory** = a restart resets the counts. **Redis** = the shared version (Stage D).
- A refused request does NOT use up quota (we check all limits first, then count).

**Important commands:**
```powershell
python -m scripts.measure_tokens               # measure tokens per answer (5 Groq calls)
$env:PUBLIC_MODE="1" ; uvicorn docpilot.api:app   # run WITH limits (like the live server)
Remove-Item Env:PUBLIC_MODE                    # back to unlimited
```
Groq limits page: https://console.groq.com/settings/limits

**Note for later (Stage B):** behind Caddy every visitor would look like Caddy's IP, so
uvicorn needs `--proxy-headers`.

---

## Step A3: queue instead of crash (2026-10-23) - built, unit tests

**Problem:** 20 questions at the same second = 20 reranker runs at once on 2 CPUs and
2 GB RAM. Memory spikes and the server can be killed (OOM = out of memory).

**Simple picture: a barber shop with 2 chairs and a waiting bench.** 2 answers run at the
same time. The 3rd person sits on the bench (up to 30 seconds) and the screen says
"Waiting in line: DocPilot is busy". If no chair frees up in time, they get the busy sign.

**What we built:** a **BoundedSemaphore(2)** in `limits.py`.
- **Semaphore** = a counter of free seats. `acquire()` takes a seat (or waits),
  `release()` gives it back.
- **Bounded** = giving back more seats than were taken is an error, so a bug can never
  create a 3rd chair.
- The seat is given back in `finally`, so it comes back even when the user presses Stop.
- Used by the chat stream AND `/ask`, on the laptop too (costs nothing).

**Result:** extra traffic becomes WAITING time, not a crash. Memory stays about flat.

**Why a threading semaphore (not asyncio)?** Our endpoints are plain `def` functions that
FastAPI runs in a thread pool. **Why not Celery + Redis?** A real job queue needs a broker
server; that is Stage D.

---

## Step A4: friendly "busy" sign (2026-10-23) - built, unit tests

**Problem:** when Groq's quota for the minute is used up, Groq answers **429**. The openai
library retries twice by itself; if it still fails, the user used to see "Something went
wrong". That is wrong: it is not a bug, just a busy minute.

**Simple picture: a "kitchen busy, back in a minute" sign** instead of a broken door.

**What we built:**
- Chat stream: Groq 429 -> `{"type": "error", "message": "DocPilot is busy right now (free
  demo). Please try again in a minute."}`
- `/ask`: the same message with **503** (Service Unavailable = busy, try later).
- Tests use a FAKE 429 (a real one would waste my daily quota).

**Status codes so far:** 400 bad request (bad visitor id, too many files), 404 not yours /
not found, 429 you hit a limit, 503 the service is busy.

**Important commands (tests, for every step):**
```powershell
$env:GROQ_API_KEY="" ; $env:LLM_MODEL="" ; $env:MLFLOW_DISABLE_AGENT_HINT="1" ; python -m pytest -q
ruff check src tests ; ruff format --check src tests
python scripts/check_file_lengths.py
```
Result after A1-A4: **326 tests pass**.

---

## Step A5: uploaded files' vectors live on disk (2026-10-23) - built, checked on Docker

**Problem:** the server has only 2 GB RAM but 20 GB disk. Every visitor's upload adds
vectors. If they all stay in RAM, memory grows until the server dies.

**Simple picture: the store room.** The kitchen counter (RAM) is small and fast; the store
room (disk) is big and a bit slower. Things used every minute stay on the counter (the
main library: every question searches it). Things used rarely go to the store room (each
visitor's uploads: only their own chat searches them).

**What we built:** the uploads collection is created "cold".
| Setting | Meaning |
|---|---|
| `memory = cold` (dense vectors, sparse index, payload) | kept on disk, read only when a search needs it |
| payload index on `chat_id` and `source` | a tiny "table of contents" kept in RAM, so filtering "only this chat's files" never digs in the store room |

**Small words:**
- **Memory-mapped (mmap)** = the operating system loads only the pieces of a disk file
  that are being used.
- Qdrant 1.19 has 3 levels: `cold` (disk, loaded when used), `cached` (pre-loaded but may
  be pushed out), `pinned` (always in RAM).
- **Verify before use paid off:** the plan said `on_disk=True`, but in Qdrant 1.19 that
  flag is DEPRECATED; the new name is `memory`. I checked the installed library and
  qdrant.tech before writing code.

**Real check:** made a temporary collection on the Docker Qdrant (1.19.1), read its
settings back: dense `cold`, sparse `cold`, payload `cold`, indexes `chat_id` + `source`.
Then deleted it.

**Note:** my laptop's existing uploads collection was made before this change and keeps
the old settings. The live server starts fresh, so it gets the new ones.

---

## Step A6: cleaning at night (2026-10-23) - built, unit tests

**Problem:** a public demo collects junk forever: chats, PDFs, vectors. The 20 GB disk
would fill up one day.

**Simple picture: a shop cleans the tables every night.** Anything nobody touched for a
week goes.

**What we built:** `src/docpilot/chat/cleanup.py`
- Every hour, a background thread deletes chats with no activity for **7 days**.
- It deletes everything: vectors, then uploaded files, then the database rows. That order
  matters: if a step fails, the row is still there, so the next round tries again.
  (Rows first would leave "orphan" vectors nobody can find.)
- The "delete chat" button now uses the SAME function (`delete_everything`), so the
  button and the cleanup can never behave differently.
- Public mode only: on my laptop, my chats stay.

**Small words:**
- **Daemon thread** = a helper thread that stops by itself when the app stops.
- `Event.wait(3600)` = "sleep one hour, but wake up at once if the app is shutting down".

**Why not cron or Celery beat?** Extra programs to install and run for one small job.

---

## Step A7: OPEN / CLOSED sign (2026-10-23) - built, unit tests

**Problem:** `/health` only says "the program is running". But the app can be running
and still unable to answer: Qdrant is down, or the library is missing.

**Simple picture:** `/health` = the shop lights are on. `/ready` = the cook is in AND the
fridge is full, so you can actually order food.

| Endpoint | Checks | 200 / 503 |
|---|---|---|
| `/health` | the process is alive | always 200 if running |
| `/ready` (new) | models loaded, Qdrant answers, main library exists, LLM model set | 200 = ready, 503 = not ready (+ which check failed) |

- It does NOT call Groq: a monitor checks every few minutes and would waste the quota.
- Who uses it later: UptimeRobot (Stage C) and me. Docker uses `/health` to restart a
  dead process. Kubernetes has the same two ideas: **liveness** and **readiness** probes.

**Important commands:**
```powershell
uvicorn docpilot.api:app                       # restart first! (old code has no /ready)
curl.exe http://127.0.0.1:8000/ready           # {"status":"ready","checks":{...}}
curl.exe http://127.0.0.1:8000/health          # {"status":"ok"}
```
Try it: stop Qdrant (`docker compose stop qdrant`), call `/ready` (should be 503), then
`docker compose start qdrant`. NEVER `docker compose down -v` (deletes the data).

Result after A1-A7: **332 tests pass**. Stage A code is complete.

---

**My check (live, 2026-10-23):** restarted the server (old code gave 404 on `/ready`).
`/ready` = ready, all 4 checks true. `docker compose stop qdrant` -> `/ready` =
`not_ready` (`qdrant: false`, `library: false`) but `/health` = ok: lights on, kitchen
closed. `docker compose start qdrant` -> back. PASS.

---

## Stage B starts: Docker images (2026-10-23)

**Teach first:** `03_teach_docker_images.md` (image vs container, layers and cache,
multi-stage, `.dockerignore`, env vars, volumes, interview questions).
**Folder rule (my request):** all production teaching, interview notes and this log live
in `docs/production/` only. The Stage A primer moved here as `02_teach_public_app_safety.md`.

---

## Step B1: `.dockerignore` (2026-10-23) - built, checked

**Problem:** `docker build .` sends the whole project folder to the builder. Without a
filter, my `.env` (Groq key!), `.venv` (GBs), data and notes could end up in the image.
An image pushed to a registry can be downloaded by anyone.

**Simple picture: packing for a trip,** with a list of things that stay at home.

**What we built:** `.dockerignore` keeps out: `.env`, `.venv`, caches, `data/`, Qdrant
folders, `*.db`, `.git`, `docs/`, `tests/`, `evals/`, `labs/`, `ui/`, `scripts/`.
The image gets only `src/`, `web/` (to build the UI) and the two requirements files.

**Check:** `docker run --rm docpilot:dev sh -c "ls -a /app"` -> `.cache data
requirements-lock.txt requirements-server.txt src web`. **No `.env`.** PASS.

---

## Step B2: the Dockerfile (2026-10-23) - built, checked offline

**Simple picture: a packed lunch box.** Everything the app needs, sealed in one box, so
any server can open it and get the exact same app.

**What we built:**
| File | What it is |
|---|---|
| `Dockerfile` | the recipe: 2 stages (Node builds the UI, then Python runs the app) |
| `requirements-server.txt` (new) | the server's packages: same pins, WITHOUT Docling and OpenCV, WITH `pypdfium2` named directly |

**The recipe, step by step:**
```text
Stage 1 "web"  node:22.23.4-bookworm-slim : npm ci -> npm run build -> /web/dist
Stage 2 "app"  python:3.13.17-slim-bookworm
  1. pip install torch 2.14.1 CPU-only      (no GPU on the server; no GBs of CUDA)
  2. pip install requirements-server.txt -c requirements-lock.txt   (same versions as laptop)
  3. make a non-root user "docpilot"
  4. COPY src/ and the built UI from stage 1 (Node itself stays behind)
  5. bake the 3 models in (run warm_up_models during the build)
  6. HF_HUB_OFFLINE=1 + BM25_MODEL_PATH   (never download at start)
  7. HEALTHCHECK /health ; CMD uvicorn ... --host 0.0.0.0 --port 8000
```

**Small words:**
- **Layer cache:** every line is a cached layer; Docker rebuilds from the first changed
  line down. My second build said `CACHED` for steps 1-4 and only redid steps 5-7 (my code
  changed). That is why slow steps go first.
- **Multi-stage:** build tools (Node) stay in the workshop; only the finished table ships.
- **`0.0.0.0`:** "listen on every network card of the container". `127.0.0.1` would only
  accept calls from inside the container itself.
- **Non-root user:** if someone breaks in through the app, they are not the boss of the box.

**Measured BEFORE choosing what to leave out:** I imported the app and listed which big
libraries it loads: only `sentence_transformers`, `fastembed`, `torchvision`, `boto3`.
Docling and OpenCV are never loaded, so they stay out of the image.

**The bug the offline test found (good interview story):**
- Test: start the image with **no network** (`--network none`) and load the models.
- Result: BGE and the reranker loaded, but **BM25 failed**: "Could not load model
  Qdrant/bm25 from any source", although its files were in the cache.
- Cause: fastembed 0.8.1's "is it already downloaded?" check wants 2 files (`mock.file`,
  `tamil.txt`) that the Hugging Face repo does not have. Online, it silently re-checks the
  internet on every start (my laptop hid the bug). Offline, it gives up.
- Fix: fastembed's `specific_model_path` option = "the files are here, don't check". The
  image sets `BM25_MODEL_PATH=/app/.cache/bm25`; on the laptop it stays empty (no change).
- After the fix: `OFFLINE OK`, torchvision not even needed.
- **Lesson:** "works on my laptop" can hide a network dependency. Test the box the way
  the server will run it.

**Other checks:** runs as user `docpilot` (not root); 332 laptop tests still pass.

**Image size (my run, 2026-10-23):** I predicted **1.5 GB**; real **1.86 GB** (Docker's
"disk usage"; about 25% more than my guess). Where it goes (`docker history`):

| Layer | Size | Share |
|---|---|---|
| CPU-only torch | 873 MB | 47% (the biggest single piece, even WITHOUT CUDA) |
| app packages (transformers, onnxruntime, qdrant-client, ...) | 638 MB | 34% |
| the 3 baked models | 226 MB | 12% |
| Debian + Python base | about 120 MB | 7% |
| my code + the React build | 0.6 MB | 0.03% |

**Lessons:** my own code is almost nothing; the ML libraries are the box. If I want a
smaller image later, the biggest win is replacing torch (for example running BGE and the
reranker with ONNX Runtime, which fastembed already uses) - not trimming my code.
On the 20 GB server disk, 1.86 GB is fine; it costs pull time (once per deploy).

**Known trade-off:** step 5 (bake models) comes after `COPY src/`, so any code change
re-downloads the models in the build (about 2 minutes). Fine for now; can be improved.

**Important commands:**
```powershell
docker build -t docpilot:dev .                                   # build (first time: ~10 min)
docker images docpilot                                           # the image and its SIZE
docker history docpilot:dev                                      # size of each layer
docker run --rm --network none docpilot:dev python -c "from docpilot.retrieval.pipeline import warm_up_models; warm_up_models(); print('OFFLINE OK')"
docker run --rm docpilot:dev sh -c "whoami; ls -a /app"          # non-root? no .env?
```

---

## Step B3: the production stack + Caddy (2026-10-23) - built, validated

**Teach first:** `04_teach_https_dns_caddy.md` (DNS, HTTPS, certificates, reverse proxy,
why Caddy, Compose networking, interview questions).

**Problem:** the server must run 3 things together (front door, app, database), only the
front door may face the internet, and visitors must get HTTPS (the padlock).

**Simple picture: an apartment building.** Caddy is the security guard at the gate: it
opens the sealed envelopes (HTTPS) and walks visitors to the right flat. The app and
Qdrant are flats with no door to the street.

**What we built:**
| File | What it does |
|---|---|
| `docker-compose.prod.yml` | starts `caddy` + `app` + `qdrant`; only Caddy has ports (80, 443) |
| `deploy/Caddyfile` | 3 lines: my domain -> gzip -> forward to `app:8000` |

**Key settings (and why):**
| Setting | Why |
|---|---|
| `QDRANT_URL=http://qdrant:6333` | inside Compose, containers find each other by NAME |
| `PUBLIC_MODE=1` | turns on A2 limits, A6 cleanup, smaller uploads |
| `FORWARDED_ALLOW_IPS=*` | the app uses the visitor's real IP from Caddy (for A2). Safe only because port 8000 is not public |
| volumes `caddy_data`, `app_data`, `qdrant_data` | certificates, chats/uploads and the index survive restarts and upgrades |
| `restart: unless-stopped` | crash or reboot -> Docker starts it again |
| `mem_limit` 128m / 1400m / 600m | if one container goes wild, only IT is killed (first guesses; B6 measures) |

**Verified before writing:** Caddy 2.11.7 exists for amd64 + arm64; Caddy flushes
streaming replies (`text/event-stream`) at once, so live answers still stream; it sets
`X-Forwarded-For` by default.

**Checks so far:** `docker compose -f docker-compose.prod.yml config --quiet` = valid;
`caddy validate` = "Valid configuration".

**Important commands:**
```powershell
$env:APP_IMAGE="docpilot:dev"                                  # use my local image
docker compose -f docker-compose.prod.yml up -d                # start the 3 containers
docker compose -f docker-compose.prod.yml ps                   # are they up / healthy?
docker compose -f docker-compose.prod.yml logs app --tail 30   # what the app printed
curl.exe -k https://localhost/ready                            # -k: accept Caddy's local certificate
docker compose -f docker-compose.prod.yml down                 # stop (NEVER add -v)
```

---

## Stage A summary (what I can say in an interview)

> "Before putting a laptop app on a public link, I made it safe for strangers: private
> chats per visitor with a random id (404 for others), rate limits set from MEASURED token
> use against Groq's free limits (tokens per minute run out first, not requests), a
> semaphore so at most 2 answers run at once on a 2 GB server, a friendly busy message on
> 429, upload vectors on disk with RAM payload indexes, an hourly cleanup of idle chats,
> and a readiness endpoint separate from health."

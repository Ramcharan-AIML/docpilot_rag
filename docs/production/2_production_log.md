# Production log (part 2)

Continues [01_production_log.md](01_production_log.md) (500-line rule). Same format:
one section per step, newest at the BOTTOM.

---

## Step B3 result: the prod stack runs on my laptop (2026-10-24) - PASS

**What I ran:**
```powershell
$env:APP_IMAGE="docpilot:dev"
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
curl.exe -k https://localhost/ready
curl.exe -k -I https://localhost/
docker compose -f docker-compose.prod.yml down
```

**What it showed:**
| Check | Result | Meaning |
|---|---|---|
| `up -d` | network + 4 volumes created, 3 containers started | the whole building in one command |
| `ps` | app `Up (healthy)`; Caddy ports 80 + 443; app and Qdrant show only inside ports (`8000/tcp`, `6333-6334/tcp`) | the HEALTHCHECK works; only Caddy faces the outside |
| `/ready` through Caddy | `not_ready`: models, qdrant, llm true; **library false** | expected: the prod Qdrant has a brand-new EMPTY volume (the main library is copied in by B4) |
| `-I https://localhost/` | `200 OK`, `Via: 1.1 Caddy`, `Server: uvicorn`, `Alt-Svc: h3` | HTTPS works; the request really went guard (Caddy) -> flat (uvicorn); HTTP/3 offered |
| `down` | containers + network "Removed" | normal: see below |

**What "Removed" means (my question):** `down` stops the containers and DELETES them
plus the private network. That is fine: containers are disposable boxes; the next `up`
makes fresh ones from the same image in seconds. What stays:
- the **image** `docpilot:dev` (the packed lunch box)
- the 4 **volumes** (`app_data`, `qdrant_data`, `caddy_data`, `caddy_config`): `down` does
  not list them because it does not touch them. Only `down -v` deletes volumes. Never.

**Note:** my laptop stack (`docker compose up -d`: Qdrant, SeaweedFS, MLflow) ran at the
same time without a clash: different project names (`docpilot_rag` vs `docpilot-prod`),
and the prod Qdrant publishes no port.

---

## Decision: what the website answers from (2026-10-24)

**My question:** should the website have no built-in documents ("upload a doc first"),
or a demo library with a switch?

**Mentor's advice (I agreed):** keep a **demo library**, because:
- a recruiter opening the link usually has no document ready: an empty app = closed tab;
- every number I measured (R@5 0.878, 0 made-up facts, red team 0/18) is on this library;
- the project plan (D-030) says DocPilot is a docs assistant, not "chat with any file".

**My rules for it:**
| Rule | What it means |
|---|---|
| No personal notes online | my interview notes are `local_only`: laptop yes, website no |
| Show the library professionally | cards on the welcome screen: name, type, documents, licence |
| A switch with a lock | "Demo library" ON in a new chat; after I attach a file, the chat answers ONLY from my files ("Your files only" + lock icon) until I start a new chat |
| Helpful messages | not found -> says what the library covers + "attach your own file" |

---

## UI step: demo library panel + switch + lock + messages (2026-10-24) - built, checked

**Simple picture: a library with a reading room.** The shelf of demo books is shown at
the entrance (the panel). You can read from the shelf (switch ON), or bring your own book
into a private room (attach a file). Once you are in your room, you read only your book
(the lock); to use the shelf again, take a new room (New chat).

**What we built:**
| File | Change |
|---|---|
| `src/docpilot/library.py` (new) | builds the panel list from what the index REALLY holds + titles/licences from the register |
| `chat_api.py` | `GET /api/library`; the toggle values `main` / `off` / `files` |
| `chat/service.py` | the lock + 3 new messages (library off, file still preparing, not found + hint), all BEFORE any LLM call |
| `ingestion/sources.py` | titles for each source; interview notes -> `local_only` |
| `web/src/components/LibraryPanel.jsx` (new) | the cards on the welcome screen |
| `web/src/components/Composer.jsx` | the old dropdown -> a "Demo library" switch / "Your files only" lock |
| `App.jsx`, `api.js`, `styles.css`, `Icons.jsx` | wiring, styles (light + dark), 3 small icons |

**Why the server ALSO enforces the lock (not only the UI):** anyone can send requests
without my UI (curl). Rules that matter live on the server; the UI only shows them.

**Why the panel reads the live index (not a hard-coded list):** it can never show a
document the site does not have. On my laptop it lists my notes; on the website it can't.

**Messages (no Groq call spent on them):**
| Situation | Answer |
|---|---|
| Switch off, no file | "The demo library is switched off and this chat has no files yet. Attach a PDF, Markdown or text file (the paperclip), or switch the demo library on." |
| File still being prepared | "Your file is still being prepared. Ask again when it shows a green tick." |
| Not found (library) | "I could not find this in the documents. The demo library covers FastAPI, Pydantic, Docker and RAG / LLM papers. To ask about something else, attach your own PDF, Markdown or text file (the paperclip)." |
| Not found (my files) | "I could not find this in the documents. I searched only the files in this chat." |

**Tests:** 340 pass (new: lock, failed upload does not lock, library off, not-found hints,
library list, seed). React build OK.

---

## Step B4: the seed index - moving house with a packed box (2026-10-24) - DONE

**Problem:** the production Qdrant starts EMPTY. Rebuilding the library on the server
would need Docling (not in the image), the downloaded docs, and minutes of embedding.

**Simple picture: moving house.** Pack the finished library into one box on the laptop
(a **snapshot**), carry the box, unpack it on the server. Nothing is rebuilt.

**Small words:**
- **Snapshot** = one file with a whole Qdrant collection: vectors, texts, settings.
- **sha256 checksum** = the file's fingerprint. Qdrant compares it and refuses a damaged
  copy (a half-downloaded file would otherwise give a broken library).
- **Idempotent** = safe to run twice: the second run sees the library and does nothing.

**What we built:**
| File | Where it runs | What it does |
|---|---|---|
| `scripts/make_public_snapshot.py` | laptop | copies the library WITHOUT `local_only` sources into a temporary collection (vectors copied, no re-embedding), snapshots it, saves `.snapshot` + `.sha256` in `data/snapshots/` (gitignored), cleans up |
| `src/docpilot/store/seed.py` | inside the app container | uploads the file to an EMPTY Qdrant; skips if the library is there; `--force` replaces |

**Real results (2026-10-24):**
| Check | Result |
|---|---|
| make_public_snapshot | 453 chunks, left out `interview`: **40**, kept **413**; file **3.1 MB** |
| laptop library afterwards | still 453 (untouched), temp collection deleted |
| seed (1st run) | `restored docpilot_v1_ft200: 413 chunks` |
| seed (2nd run) | `skipped: the library is already there` (idempotent) |
| `/ready` through Caddy | `ready`: models, qdrant, library, llm all true |
| `/api/library` through Caddy | FastAPI 4 docs (68 chunks), Pydantic 3 (49), Docker 5 (56), CoT paper 1 (196), Wikipedia 3 (44); **no interview notes** |
| switch off, no file (through Caddy) | the `no_library` message, no Groq call |

**Honest notes:**
- The website library (413) is NOT the measured one (453). Questions answered from my
  notes will now get "not found" online. That is a correct refusal, not a bug.
- The `.snapshot` file must be rebuilt whenever the main library changes.

**Important commands:**
```powershell
python -m scripts.make_public_snapshot                                # laptop: pack the box
docker build -t docpilot:dev .                                        # image with the new code
$env:APP_IMAGE="docpilot:dev" ; docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml run --rm -v "${PWD}\data\snapshots:/seed:ro" app python -m docpilot.store.seed /seed/docpilot_public_2026-10-24.snapshot
curl.exe -k https://localhost/ready                                   # -> ready
curl.exe -k https://localhost/api/library                             # -> the 5 sources
```
`run --rm` = start a ONE-OFF extra container from the app image, run the command, delete
it. `-v ...:/seed:ro` = show my laptop's snapshot folder inside it, read-only.

**My check (2026-10-24):** opened https://localhost: the library cards, the switch and
the lock look good. PASS.

---

## Step B5: CD - GitHub builds the image and stores it in GHCR (2026-10-24) - built

**Teach first:** `05_teach_cicd_ghcr.md` (CI vs CD, registries, SHA tags, rollback,
GITHUB_TOKEN, least privilege, layer cache, interview questions).

**Problem:** the AWS server must download a finished image. Building it on my laptop is
not repeatable and not linked to a commit.

**Simple picture: a bakery.** CI checks every batch of dough (tests). CD packs the bread
that passed and puts it on the delivery shelf (GHCR). The van (deploy) is me, for now.

**What we built:** `.github/workflows/image.yml`
```text
merge a PR into main -> ci.yml (tests + eval gate)
   -> only if GREEN: image.yml
        checkout THAT commit -> Buildx -> log in to ghcr.io with GITHUB_TOKEN
        -> build linux/amd64 -> push :sha-xxxxxxx and :latest
```

**Key choices:**
| Choice | Why |
|---|---|
| `workflow_run` + "only if success" | no image from broken code |
| `GITHUB_TOKEN` + `packages: write` only | no secret to create; least privilege |
| tag `sha-<commit>` | the server pins exact code; rollback = previous tag |
| actions pinned (e.g. `login-action@v4.6.0`) | nobody else's change can silently change my pipeline. v4.7.0 was 1 day old: skipped |
| `cache type=gha` | code-only changes do not reinstall torch |
| amd64 only | t3.small is Intel/AMD; ARM later for Oracle |

**Checks so far:** `actionlint 1.7.12` (run in Docker) = no problems in `image.yml` and
`ci.yml`. The real run happens after the merge to main.

**Important commands (I run these):**
```powershell
gh pr create --base main --head production --title "Phase 7: public-safe app, Docker image, prod stack, demo library, CD" --body "Stage A, B1-B5 (D-063..D-067). Details: docs/production/."
gh pr checks --watch                         # wait for test + eval-gate + GitGuardian
gh pr merge --merge                          # merge into main -> CI on main -> image.yml
gh run list --workflow image.yml --limit 3   # find the image run
gh run watch                                 # follow it live (pick the image run)
docker pull ghcr.io/ramcharan-aiml/docpilot:latest   # after making the package public
```

**First real run (2026-10-24):**
| What | Result |
|---|---|
| PR #7 production -> main | GitGuardian, eval-gate (1m55s), test (2m25s): all green; merged |
| `ci` on main (push) | success |
| `image` started by itself after CI | yes: the `workflow_run` trigger works |
| `image` build | **FAILED** at the tag step: "Cannot infer ref from detached HEAD" |

**Why it failed (simple):** to build EXACTLY the commit CI tested, the workflow checks out
that commit by its id. Git then is "on a commit, not on a branch" (a **detached HEAD**:
like opening a book at page 214 without knowing which chapter). `metadata-action` in
`context: git` mode wants to know the branch, so it stopped.

**Fix:** a small step reads the commit id itself (`git rev-parse HEAD`) and we write the
tag `sha-<first 7 characters>` ourselves. Same result, no branch needed. actionlint: clean.

**Lesson:** a pipeline is code too: it can only be fully tested by running it. The
first run found a mix of two settings (checkout by commit + git context) that the linter
cannot see. I predicted 3 minutes; it failed after about 15 seconds of the build job.

**Second real run, after the fix (2026-10-24) - PASS:**
| What | Result |
|---|---|
| fix PR merged -> `ci` on main | success |
| `image` run 40066900526 (started by itself) | **success in 3 min 33 s** (cold cache). My prediction: 3 min. Close. |
| tags in GHCR | `latest` and `sha-2a64dc0` (commit `2a64dc0743369e602585ce3a274323ec9cc924c7`) |
| package visibility | changed to **public** (so the server can pull without a password) |
| `docker pull ghcr.io/ramcharan-aiml/docpilot:latest` on my laptop | worked; 4 layers "Already exists" (the Python base image was already on my laptop), 8 new layers downloaded; image **1.86 GB**, same as my local build |

**Why "Already exists" (small concept):** an image is a stack of layers, each with a
fingerprint (sha256). Docker downloads only the layers it does not have yet. Like a
puzzle box where you already own the 4 corner pieces: you only buy the rest.

**Why it was faster than I feared (the plan said about 10 min for torch):** GitHub's
runners have a fast network, and torch CPU is one big wheel download, not a compile.
The next build should be faster again (layer cache `type=gha`): to be measured.

**Important commands:**
```powershell
gh pr create --base main --head production --title "B5 fix: image tag from the exact commit" --body "Fixes image.yml run 40065210124 (Cannot infer ref from detached HEAD). D-067."
gh pr checks --watch
gh pr merge --merge
gh run list --workflow image.yml --limit 3
gh run watch
docker pull ghcr.io/ramcharan-aiml/docpilot:latest
```
**B5: DONE.**

---

## Step B6: measure the prod stack in Linux containers (2026-10-24) - started

**Problem:** the AWS `t3.small` has 2 GB RAM. Before Stage C we must KNOW (not guess)
that app + Qdrant + Caddy + Linux fit. Windows numbers from Phase 6 do not count: the
containers run Linux inside Docker's VM.

**Simple picture: packing a suitcase.** Before the flight (AWS), weigh every bag at home
(B6). If the total is over the limit, decide now: a bigger suitcase (bigger server) or
another airline (Oracle, 12 GB). Not at the airport.

**What we measure:**
| Measure | How |
|---|---|
| start-up time until `/ready` | stopwatch loop from `up -d` until `"status":"ready"` |
| RAM idle | `docker stats --no-stream` |
| RAM after one question | same, right after an answer |
| RAM peak during a big upload | a sampler loop every 2 s while uploading a 258-page, 8.6 MB PDF |
| `.env` not in the image | `ls -la /app` inside a one-off container |

**My predictions (before the run):** app idle **0**, app after a question **2**,
Qdrant **2** (unit not written: recorded as given), start-up **5 s**.

**Real results (2026-10-24, laptop, Docker Desktop Linux containers, image `sha-2a64dc0`, n = 1 each):**
| Measure | My guess | Real |
|---|---|---|
| app RAM idle | 0 | **516 MiB** (torch + 3 models are loaded at start: the cook is in the kitchen before the first order) |
| app RAM after one question | 2 | **681 MiB** (the reranker and the first answer's working memory) |
| app RAM peak, 258-page upload | - | **1,100 MiB** (1.074 GiB), then it stays at about 1,022 MiB |
| Qdrant RAM | 2 | **448 MiB** idle, peak 468 MiB |
| Caddy RAM | - | 24 MiB |
| upload 258 pages / 8.6 MB | - | **105 s** to the green tick, 494 chunks (87 s of it = embedding: 16 batches of about 5.5 s) |
| start-up until `/ready` | 5 s | about **78 s** (container timestamps; my stopwatch said 119 s, see below) |
| `.env` in the image | - | **absent**: `/app` has only `.cache`, `data`, `src`, `web`, 2 requirements files |

**Why the stopwatch said 119 s (mentor's mistake in the commands):** `$t = Get-Date`
started the clock, but I typed the next commands one by one, so my typing time was
counted. The container timestamps are exact: Qdrant started 06:54:15, the first
`/ready 200` was 06:55:33.9. Lesson: measure with the system's own clocks (logs), not a
stopwatch that includes a human.

**Why start-up takes about 78 s:** 72 s is Python IMPORTING torch, transformers and
sentence-transformers (reading thousands of files). Loading the model weights is only
about 5 s. A bare `import docpilot.api` takes 46-57 s in a fresh container and 70 s on
Windows itself: the laptop is slow at this, not Docker.

**Why memory does not go down after the upload (small concept):** Python keeps the
memory it freed for later, like a restaurant that keeps the extra tables after a
party. It is reused for the next upload, so the peak (1,100) is what matters, not "back
to idle".

**Does it fit the t3.small (2 GB)?**
```text
Caddy 24 + app 1,100 (peak) + Qdrant 468 = about 1,590 MiB
+ Linux + Docker about 300-400 MiB      = about 1.9-2.0 GB   -> tight; 2 GB swap = safety net
```
Not "clearly above 2 GB" (the plan's decision point), so: **keep t3.small** (D-068).

**What changed:**
| File | Change | Why |
|---|---|---|
| `docker-compose.prod.yml` | limits kept 128m / 1400m / 600m, comments now hold the real numbers | each limit is about 25 % above its measured peak |
| `Dockerfile` | HEALTHCHECK `start-period` 60 s -> **180 s** | 78 s on a 20-thread laptop; the server has 2 vCPUs |
| `docs/3_decisions.md` | D-068 | the measurement + decision |

**Honest notes:** n = 1 run each, laptop not server. Everything is re-measured on the
real server in Stage C. The new `start-period` reaches GHCR with the next merge to main.

**Important commands:**
```powershell
docker compose -f docker-compose.prod.yml up -d
docker stats --no-stream --format "table {{.Name}}`t{{.MemUsage}}`t{{.CPUPerc}}"
1..90 | ForEach-Object { docker stats --no-stream --format "{{.Name}} {{.MemUsage}}" docpilot-prod-app-1 docpilot-prod-qdrant-1; Start-Sleep 2 }
docker inspect -f '{{.Name}} started {{.State.StartedAt}}' docpilot-prod-app-1
docker logs -t docpilot-prod-app-1                     # -t = timestamps on every line
docker run --rm ghcr.io/ramcharan-aiml/docpilot:latest ls -la /app
```
**B6: DONE.**


---

Continues in [3_production_log.md](3_production_log.md) (500-line rule).

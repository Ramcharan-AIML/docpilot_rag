# Teach: Docker images (Stage B, from zero)

Simple English. Written 2026-10-23, before the Dockerfile is built. Real numbers (image
size, RAM, start-up time) are added after we measure them in B6. Until then: n/a.

---

## 1. Why Docker for going live?

Today DocPilot runs on my laptop because my laptop has: Python 3.13, the right packages,
the models in a cache folder, the React build, Windows paths... A new server has NONE of
that. Installing it all by hand on the server = slow, easy to get wrong, hard to repeat.

**Real-life example: a lunch box.** Instead of telling a friend "go buy rice, dal, salt,
cook it at 180 degrees...", I pack the finished food in a box. Anyone can open it anywhere
and eat the same meal. Docker packs the app + everything it needs into one box.

| Word | Meaning | Lunch-box picture |
|---|---|---|
| **Image** | a frozen, read-only package: OS files + Python + packages + my code + models | the packed lunch box (the recipe result, sealed) |
| **Container** | a running copy of an image | opening the box and eating; many people can open copies of the same box |
| **Dockerfile** | the step-by-step recipe that builds the image | the recipe card |
| **Registry** | a shop that stores images (Docker Hub, GHCR) | a shared fridge where boxes wait to be picked up |
| **Tag** | the image's version label, e.g. `qdrant/qdrant:v1.19.1` | the date sticker on the box |

**Image vs container in one line:** an image is a class, a container is an object.

---

## 2. Layers and the build cache (why the ORDER of lines matters)

Each line in a Dockerfile (`FROM`, `RUN`, `COPY`) makes one **layer**: a thin sheet of
file changes stacked on the one below. Docker remembers (caches) every layer. When I build
again, it reuses every layer until the FIRST line whose input changed; from there on,
everything is rebuilt.

```text
FROM python:3.13.17-slim         <- layer 1  (rarely changes)
RUN pip install torch (CPU)      <- layer 2  (big, slow, rarely changes)
COPY requirements-server.txt     <- layer 3
RUN pip install -r ...           <- layer 4  (slow; only rebuilt if requirements change)
COPY src/                        <- layer 5  (changes often: my code)
```

**Rule:** put slow things that rarely change FIRST, and my code LAST. If `COPY src/` came
before `pip install`, every tiny code change would reinstall all packages (minutes).

**Real-life example:** a stack of plates. To change the 4th plate you lift off everything
above it, but the bottom 3 stay put.

---

## 3. Multi-stage builds (leave the tools behind)

The React app needs **Node.js** to BUILD (turn `.jsx` into plain `.js` files). After the
build, Node is useless: FastAPI just serves the finished files.

```text
Stage 1 "web":  node:22 image -> npm ci -> npm run build -> web/dist (small files)
Stage 2 "app":  python:3.13-slim -> ... -> COPY --from=web  web/dist   (only the result)
```

The final image contains ONLY stage 2. Node and its hundreds of MB of tools never reach
the server. **Real-life example:** a carpenter builds a table in the workshop, then ships
only the table, not the workshop.

---

## 4. Our image's choices (each with why / why not)

| Choice | Why | Why not the other way |
|---|---|---|
| `python:3.13.17-slim-bookworm` | same Python minor as the laptop (3.13); "slim" = small Debian without extras | `python:3.13` full: about 1 GB of compilers we don't need. `alpine`: tiny, but many ML wheels don't support it (musl), so builds from source |
| Exact tag (`3.13.17`), never `latest` | the same build every time | `latest` changes under me silently |
| **CPU-only torch** (from download.pytorch.org/whl/cpu) | the server has no GPU | the default Linux torch pulls several GB of NVIDIA CUDA libraries |
| **No Docling / OpenCV in the image** | the running app never imports them (checked: only sentence-transformers, fastembed, boto3 load); uploads use the fast `pypdfium2` reader | they are big and only build the main library, which happens on the laptop |
| **Models baked in** (downloaded during the build) | the server starts with no internet download and no wait | download on start: slow first boot, breaks if Hugging Face is down |
| `HF_HUB_OFFLINE=1` at run time | proves the image never downloads anything when it starts | without it, a missing file would silently download |
| **Non-root user** `docpilot` | if someone breaks in through the app, they get fewer powers | root inside the container = full control of it |
| `HEALTHCHECK` on `/health` | Docker marks the container unhealthy if the process hangs | no check = a frozen app looks "running" |
| `.dockerignore` | keeps `.env` (secrets), `.venv`, data, docs out of the image | without it, `COPY . .` could put my Groq key inside a public image |

---

## 5. `.dockerignore` (the most important safety file)

When I run `docker build .`, Docker first sends the folder (the **build context**) to the
builder. `.dockerignore` lists what must NOT be sent. **Real-life example:** packing for a
trip: a list of things that stay home (passport copies of other people, the house keys).

Most important line: `.env`. If my Groq key got into an image that I push to a public
registry, anyone could download the image and read the key. (We test this in B6:
`docker run --rm <image> ls -a /app` must show no `.env`.)

---

## 6. Environment variables, volumes, ports (how a container talks to the world)

| Thing | Meaning | DocPilot example |
|---|---|---|
| **Environment variable** | a setting given at start, not baked in | `GROQ_API_KEY`, `PUBLIC_MODE=1`, `QDRANT_URL=http://qdrant:6333` |
| **Volume** | a folder that lives OUTSIDE the container, so data survives restarts and upgrades | `data/` (SQLite chats + uploads), Qdrant storage |
| **Port** | the door number the app listens on | 8000 inside; only Caddy talks to it (Stage B3) |

A container is **disposable**: I can delete it and start a new one from the image any
time. Anything written inside it (not in a volume) is LOST then. That is why chats and
uploads go to a volume.

---

## 7. Commands I will use

```powershell
docker build -t docpilot:dev .                  # build the image from the Dockerfile
docker images docpilot                          # list it, with its SIZE
docker run --rm -p 8000:8000 --env-file .env docpilot:dev   # run it, my keys from .env
docker ps                                       # running containers
docker stats --no-stream                        # RAM / CPU per container, right now
docker logs <name>                              # what the app printed
docker run --rm docpilot:dev ls -a /app         # look inside: no .env allowed!
docker history docpilot:dev                     # the layers and how big each one is
```

`--rm` = delete the container when it stops (no clutter). `-p 8000:8000` = laptop port
8000 -> container port 8000. `--env-file .env` = give the secrets at RUN time (they are
never inside the image).

---

## 8. Interview questions

**Q1. Image vs container?** An image is the read-only package (like a class); a container
is a running instance of it (like an object). Many containers can run from one image.

**Q2. Why does the order of Dockerfile lines matter?** Every line is a cached layer.
Docker rebuilds from the first changed line down, so slow, stable steps (installing
packages) go first and my often-changing code goes last.

**Q3. What is a multi-stage build?** Several `FROM` stages in one Dockerfile; the final
image copies only the results it needs from earlier stages (our React build without
Node), so it stays small and has fewer tools an attacker could use.

**Q4. How do you keep secrets out of an image?** `.dockerignore` excludes `.env`; secrets
come in at run time as environment variables (later from AWS SSM Parameter Store);
verify by listing the image's files.

**Q5. Why CPU-only torch?** No GPU on the server; the default wheel bundles CUDA libraries
of several GB that would only make the image bigger and slower to pull.

**Q6. Why bake the models into the image?** No download at start-up (fast, works offline,
does not depend on Hugging Face being up); the trade-off is a bigger image.

---

## 9. Real results (filled after each step)

| Step | Result | Date |
|---|---|---|
| B1 `.dockerignore` | `/app` holds only `.cache data requirements-* src web`: no `.env` | 2026-10-23 |
| B2 Dockerfile | builds; second build reused cached layers 1-4; runs as `docpilot` | 2026-10-23 |
| Offline start | first try FAILED (fastembed BM25 offline check wants 2 files its repo lacks); fixed with `BM25_MODEL_PATH`; then all 3 models load with `--network none` | 2026-10-23 |
| Image size | predicted 1.5 GB, real **1.86 GB**: torch CPU 873 MB, packages 638 MB, models 226 MB, base ~120 MB, my code + UI 0.6 MB | 2026-10-23 |

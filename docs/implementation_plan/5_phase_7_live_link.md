# Phase 7 (new plan): DocPilot Live on AWS, Step by Step

Written 2026-10-23, after the hosting decision was locked (D-062). Simple English.
This plan **replaces the order** of `phase_7_production.md` to `4_phase_7_production.md`
until the live link works; those files stay as the "after submission" plan (Stage D).

**Rule for every step:** explain -> build one small thing -> test -> you read and run ->
record real numbers. Nothing in AWS is created before Step C1 is finished.
Items marked **VERIFY** are checked on official pages on the day we do that step.

---

## 0. The goal and the rules (locked)

### 0.1 Goal

One public HTTPS link, for example `https://docpilot.duckdns.org`, that:

- anyone can open (interviewers, friends, colleagues) and chat with DocPilot;
- is **always on**: no sleeping, no "wake up" wait (unlike Streamlit Cloud, Render free,
  Hugging Face free);
- costs you **₹0**: AWS free-plan credits only (the ₹2 card check is refunded);
- is live **before the submission (~2026-10-25)**.

### 0.2 Locked decisions

| Decision | Choice | Why |
|---|---|---|
| Cloud | **AWS free plan** | ₹0, reliable signup, the cloud you most want to learn |
| Server | **EC2 `t3.small`** (2 vCPU, 2 GB RAM) + 2 GB swap | Measured app peak about 1.0 GB; whole stack about 1.6-1.9 GB (re-measured in B6) |
| How long | About 5-6 months on credits | Then move to Oracle Always Free (D-018), so the link lives on |
| Fallback | **Oracle Always Free** (ARM, 1 OCPU / 6 GB) | If the India (AISPL) account shows **no credits**, launch nothing on AWS |
| Image registry | **GitHub Container Registry (GHCR)** | Free for public images; avoids ECR storage fees |
| HTTPS | **Caddy** + Let's Encrypt, name from **DuckDNS** | Both free; certificates renew by themselves |
| Server access | **SSM Session Manager** (in the browser) | No SSH port open, no key files |
| Infrastructure | **Terraform** (free program) | Everything as code; `destroy` removes it all |

### 0.3 Money safety rules (Rule 17, extended for the free plan)

| Never | Why |
|---|---|
| Click "Upgrade to paid plan" | Only then can AWS charge your card |
| Turn on AWS Organizations, Control Tower or IAM Identity Center | Can convert the free plan to paid and end the credits |
| Create a NAT gateway, load balancer, EKS cluster, or anything not in this plan | They burn credits fast |
| Use more than one region | Forgotten resources hide in other regions |
| Leave resources you do not understand | Read every `terraform plan` line before typing `yes` |
| Store AWS access keys on the laptop | Terraform runs in AWS CloudShell (VERIFY), which uses your login session |

Always: tag everything `project=docpilot`; budget alerts on; check the Billing page weekly.

### 0.4 What it costs (from credits, approximate; VERIFY on the AWS price pages in C0)

| Item | Approx. per month |
|---|---|
| EC2 `t3.small`, on 24/7 | about $15 |
| EBS disk, gp3 20 GB | about $1.6 |
| Public IPv4 address (Elastic IP) | about $3.6 |
| S3 (seed snapshot, a few MB), SSM, CloudWatch basic metrics | cents or free |
| **Total** | **about $20 / month -> $100 lasts about 5 months, $200 about 6 months** |

Free outside AWS: Terraform, GHCR (public image), GitHub Actions, DuckDNS, Caddy,
Let's Encrypt, UptimeRobot, Groq free tier.

### 0.5 The finished picture

```text
 Visitor's browser
     |  https://docpilot.duckdns.org
     v
 ┌──────────────────── AWS EC2 t3.small (Ubuntu, Docker) ────────────────────┐
 │  Caddy :443 (HTTPS, auto certificate)                                      │
 │     |                                                                      │
 │  DocPilot app :8000 (FastAPI + built React + 3 models baked in)            │
 │     |                   |                                                  │
 │  Qdrant :6333         SQLite + uploads (Docker volumes on the EBS disk)    │
 └──────────────────────────────────────────────────────────────────────────┘
     ^ image pulled from GHCR        ^ Groq key read from SSM Parameter Store
     ^ seed index from S3            ^ you connect with SSM Session Manager (no SSH)
 Outside: Groq (LLM), DuckDNS (name -> IP), UptimeRobot (emails you if down)
```

### 0.6 Timeline

| Stage | What | Needs AWS? | Rough time |
|---|---|---|---|
| A | Make the app safe to share publicly | No | half a day |
| B | Docker image, production stack, Prometheus + Grafana, re-measure RAM | No | about one day |
| C | AWS account, Terraform, deploy, HTTPS, monitoring the live server | Yes | half to one day |
| D | Everything else in the production plan | Yes | after submission |

### 0.7 Teaching map: learn each tool BEFORE we build with it

Production is the part you most want to learn, so every new tool gets a primer first
(simple English, real-life example, why / why not, interview answers), and each build step
starts with a short explanation. After the step, the real result goes into the primer.

| Before step | Learn | Primer file | Status |
|---|---|---|---|
| A1-A7 | Public-app safety: sessions vs accounts, rate limiting, concurrency, health vs readiness | `docs/production/02_teach_public_app_safety.md` | done |
| B1-B6 | **Docker images**: image vs container, layers and cache, multi-stage builds, `.dockerignore`, volumes, health checks, memory limits, image registries | `docs/production/03_teach_docker_images.md` | **new** |
| B3, C6 | **HTTPS, DNS, reverse proxy**: what a domain is, DNS records, TLS certificates, Let's Encrypt, why Caddy | `docs/production/` (teach file) | **new** |
| B5 | **CI/CD and container registries**: build pipelines, GHCR, image tags, `GITHUB_TOKEN` permissions | `docs/production/` (teach file) | **new** |
| B8 | **Prometheus + Grafana**: metrics vs logs, counters / gauges / histograms, PromQL, dashboards | `primer_prometheus_grafana.md` | exists (update with our metrics) |
| B8 | Monitoring an AI app: latency per stage, refusals, blocks | `primer_rag_monitoring.md` | exists |
| C0-C10 | **AWS**: regions, IAM (users, roles, policies, MFA), EC2, EBS, Elastic IP, security groups, S3, SSM (Session Manager + Parameter Store), CloudShell, Budgets, the free plan's rules | `primer_aws.md` + `2_primer_aws.md` | exist (add a part 3: free plan, CloudShell, SSM, our exact setup) |
| C2-C3 | **Terraform**: providers, resources, state, plan / apply / destroy, variables, outputs | `primer_terraform.md` | exists (add our real `infra/aws/` files) |
| C3 | Linux server basics: cloud-init, swap, systemd vs Docker restart, `free`, `docker stats` | inside `3_primer_aws.md` | **new section** |
| D | Kubernetes, EKS | `primer_kubernetes.md` | exists |

At the end of Stage C: `docs/project_guide/` gets a production chapter (architecture
diagram of the live system + the story), and the interview file gets the production part.

---

# Stage A: make the app safe to share (no AWS needed)

Today the app is built for ONE user on a laptop. A public link changes three things:
strangers will use it, they share one Groq quota, and they share one 2 GB server.

**Real-life example:** your home kitchen is fine for your family. Opening it as a shop
needs a door policy, a queue, and private tables.

## A1. Private chats per visitor

| | |
|---|---|
| **Problem** | Today every chat is visible to everyone: visitor B would see visitor A's chats and files in the sidebar |
| **Fix** | The browser makes a random **visitor id** once (kept in `localStorage`) and sends it in a header `X-Visitor-Id` on every call. The `chats` table gets an `owner` column. Every chat endpoint answers only the owner (others get 404, as if the chat did not exist). |
| **Files** | `chat/store.py` (owner column + migration for the existing db), `chat_api.py` (owner checks), `web/src/api.js` (header) |
| **Tests** | Visitor B cannot list, open, rename, delete, upload to, or ask in visitor A's chat |
| **Honest limit** | This is privacy, not security: there are no passwords. Real accounts (login) = Stage D |

## A2. Abuse limits (protect Groq and the server)

| Limit | Starting value (tuned later) | Why |
|---|---|---|
| Questions per visitor | 10 per minute, 60 per day | One person cannot use the whole Groq quota |
| Questions for the whole site | a daily cap below Groq's free limit (about 1,000 requests/day; VERIFY) | The demo degrades politely instead of failing |
| Files per chat | 3 | Disk and indexing time |
| Pages per file (public) | 300 | 301 pages took 94 s to index (measured) |
| File size | 20 MB | Upload time and disk |

- **Raw first** (Rule 8): an in-memory counter per visitor and per IP, in a small
  `limits.py`, no Redis yet (Redis = Stage D).
- Settings in `config.py`, switched on by `PUBLIC_MODE=1` in the server's environment, so
  the laptop stays unlimited.
- A refused request gets a clear message: "Limit reached: try again in a minute."

## A3. Concurrency cap: queue instead of crash

| | |
|---|---|
| **Problem** | 20 questions at the same moment = 20 reranker runs at once: RAM and CPU spike |
| **Fix** | A semaphore: at most **2** answers run at a time; others wait in line (a few seconds). Indexing already has ONE worker thread. |
| **Result** | Memory stays about flat whatever the traffic: extra load becomes waiting, not crashing |

## A4. "Busy" instead of an error

When Groq answers 429 (rate limit) after the retries, the stream sends
`{"type": "error", "message": "DocPilot is busy right now. Please try again in a minute."}`
and the UI shows it nicely. Tested with a fake 429.

## A5. Upload vectors on disk

The `docpilot_uploads` collection is created with vectors and payload **on disk** (Qdrant
memory-maps them; VERIFY the exact settings for qdrant-client 1.19.1). RAM then stays flat
however many files people add. The small main library stays in RAM (fast).
Estimate to check: 300 pages = about 1,400 chunks = about 5 MB of vectors and text.

## A6. Auto-cleanup of demo data

A background thread (hourly) deletes chats with no activity for **7 days**: rows, upload
folder and vectors (the same code as "delete chat"). A public demo must not fill the 20 GB
disk forever. The number of days is a setting.

## A7. Health and readiness

| Endpoint | Says | Used by |
|---|---|---|
| `/health` | the process is alive | Docker restart policy |
| `/ready` (new) | models loaded AND Qdrant reachable AND main collection present | Caddy/you/UptimeRobot: "can it answer?" |

## A8. Stage A done when

- All tests pass (new tests for A1-A7), ruff clean, file lengths OK.
- Manual check on the laptop: two browser profiles = two visitors who cannot see each
  other's chats; the 11th question in a minute is refused politely.
- Decision entry **D-063** (public-mode safety) written.

---

# Stage B: containers (no AWS needed)

Teaching first: `docs/production/03_teach_docker_images.md` (new, short; learner rule 2026-10-23: all production teaching lives in `docs/production/`): image vs container,
layers and cache, multi-stage builds, `.dockerignore`, why "models baked in" means no cold
start, environment variables, volumes, health checks, memory limits.

## B1. `.dockerignore`

Keeps the image small and secret-free: `.venv/`, `.env`, `data/`, `web/node_modules/`,
`evals/results/`, `mlruns`, `qdrant_*`, `*.db`, `.git/`, `docs/`.
**Check:** `.env` must never be inside the image (we test it in B6).

## B2. `Dockerfile` (multi-stage)

```text
Stage 1 "web"    node:22-slim     npm ci  ->  npm run build  ->  /web/dist
Stage 2 "app"    python:3.13-slim
                 pip install CPU-only torch (same version as the lock)
                 pip install the app's requirements (pinned)
                 copy src/ + web/dist from stage 1
                 bake the 3 models in (scripts/bake_models.py, pinned revisions)
                 HF_HUB_OFFLINE=1 at run time: never downloads on start
                 run as a non-root user
                 HEALTHCHECK  GET /health
                 CMD uvicorn docpilot.api:app --host 0.0.0.0 --port 8000
```

| Choice | Why | Why not the other way |
|---|---|---|
| Multi-stage | Node is needed only to BUILD the React files; the final image has no Node | One stage: hundreds of MB of Node tools in production |
| CPU-only torch | The server has no GPU; the default Linux torch pulls GBs of CUDA | Default wheel: huge image, slower pull |
| Models baked in | Start-up needs no internet and no download wait | Download on start: slow first boot, fails if Hugging Face is down |
| Docling left out of the image, if possible | Runtime uploads use pypdfium2; Docling is only for building the main library on the laptop | Keeping it: bigger image for no runtime use (decided by measuring in B6; decision entry) |
| Non-root user | A break-in gets fewer powers | Root: full container control |

**Platform:** build for `linux/amd64` (t3.small is Intel/AMD). ARM (`linux/arm64`) for the
Oracle move later.

## B3. `docker-compose.prod.yml` + `deploy/Caddyfile`

| Service | Image | Key settings |
|---|---|---|
| `caddy` | `caddy:<pinned>` (VERIFY version) | ports 80, 443; `Caddyfile`: `{$DOMAIN} { reverse_proxy app:8000 }`; volume for certificates |
| `app` | `ghcr.io/ramcharan-aiml/docpilot:<tag>` | `env_file: .env` (server only); `QDRANT_URL=http://qdrant:6333` (container name, not 127.0.0.1); `PUBLIC_MODE=1`; volume for `data/` (SQLite + uploads); `mem_limit`; `restart: always` |
| `qdrant` | `qdrant/qdrant:v1.19.1` | volume for storage; `mem_limit`; `restart: always`; not published to the internet |

MLflow and SeaweedFS stay on the laptop only (not needed to serve users).

## B4. The seed index: ship the main library without re-building it on the server

| | |
|---|---|
| **Problem** | Building the main library needs Docling (slow, memory-hungry) and the downloaded docs |
| **Fix** | Use what we already have: a **Qdrant snapshot** of `docpilot_v1_ft200` (`store/snapshots.py`). Upload it once to a private S3 bucket (C4). On first start, `scripts/seed_index.py` restores it if the collection is missing. |
| **Proof it works** | Phase 3.1b: a restored snapshot gave identical retrieval scores |

## B5. Image build in GitHub Actions (CD to GHCR)

New workflow `.github/workflows/image.yml`: on push to `main` (after CI is green), build the
image and push it to GHCR with two tags: the git commit (`sha-abc1234`) and `latest`.
Uses the built-in `GITHUB_TOKEN` (no secrets to create). The package is set to public, so
the server can pull it without a password. (VERIFY current GHCR permissions syntax.)

## B6. Run the production stack on the laptop and measure

```powershell
docker compose -f docker-compose.prod.yml up -d
docker stats --no-stream            # RAM per container, in Linux this time
```

Record in `progress.md` (real numbers, no guesses):

| Measure | Target |
|---|---|
| Image size | n/a until built |
| App container RAM: idle / after a question / during a 300-page upload | must fit with Qdrant + Caddy + OS in 2 GB (+ swap) |
| Qdrant container RAM | n/a until measured |
| Start-up time until `/ready` | n/a until measured |
| `.env` absent from the image | `docker run --rm <image> ls -a /app` shows no `.env` |

**Decision point:** if the total is clearly above 2 GB, choose before C3: a larger
free-plan type (about 3x the credit burn) or Oracle (12 GB). No guessing.

## B7. Prometheus + Grafana (monitoring, learned on the laptop first)

Teaching first: `primer_prometheus_grafana.md` (exists) + `primer_rag_monitoring.md`.

**Real-life example:** a car dashboard. Prometheus is the sensor system that writes down
the speed every few seconds; Grafana is the dashboard that draws it.

**1. The app exposes `/metrics`** (new dependency `prometheus-client`, decision entry,
VERIFY version):

| Metric | Type | Answers |
|---|---|---|
| `docpilot_stage_seconds{stage}` | histogram | p50 / p95 of input guard, condense, embed, search, rerank, first token, LLM, total |
| `docpilot_answers_total{status}` | counter | How many ok / not_found / blocked_input / blocked_output / chat / error |
| `docpilot_guard_blocks_total{reason}` | counter | Which guard rule fires, and how often |
| `docpilot_limit_refusals_total{kind}` | counter | How often A2 limits say no |
| `docpilot_uploads_total{status}` + `docpilot_indexing_seconds` | counter + histogram | Upload results and indexing time |
| `docpilot_answers_in_progress` | gauge | How many answers run right now (A3 cap = 2) |
| process memory / CPU | gauge (built in) | Is the 2 GB server safe? |

**2. Prometheus + Grafana containers on the laptop** (`docker-compose.monitoring.yml`):
Prometheus scrapes `/metrics` every 15 s; Grafana gets its data source and a DocPilot
dashboard **from files in git** (provisioning), so nobody clicks dashboards together by
hand. Panels: answers per minute by status, p50/p95 per stage, blocks by reason, memory.

**3. A small load test** (`scripts/load_test.py`, plain Python threads): several virtual
users at once, mostly **search-only** questions to save Groq quota, a few full questions.
Watch the dashboard while it runs. Record the first real **end-to-end p50 / p95 under
load** (today: n/a).

**Why on the laptop and not on the server?** Prometheus and Grafana need memory (n/a until
measured; often 100-200 MB each), and the 2 GB server is already nearly full. On the
laptop they cost the server nothing.

## B8. Stage B done when

- `https://localhost` (Caddy's local certificate) serves the app from the containers.
- Grafana on the laptop shows live DocPilot graphs; load-test numbers recorded.
- Numbers recorded; tests pass; image pushed to GHCR by CI; decision entries for new
  pieces (Caddy, GHCR, image choices, prometheus-client).

---

# Stage C: go live on AWS

Teaching first: `primer_aws.md` + `2_primer_aws.md` and `primer_terraform.md` (they exist),
plus a short "first day in AWS" checklist in this step.

## C0. Before you sign up (10 minutes)

- VERIFY on official AWS pages: t3.small price, EBS gp3 price, public IPv4 price, free-plan
  terms, and that `t3.small` is free-plan eligible in the chosen region.
- Choose the region: **Asia Pacific (Mumbai) `ap-south-1`** (close to you), if `t3.small` is
  free-plan eligible there (VERIFY in the console).

## C1. Create the AWS account safely (YOU do this; I guide click by click)

| # | Step | Done when |
|---|---|---|
| 1 | Sign up, choose the **Free plan** (not Paid) | Free plan shown in the console |
| 2 | Card check (₹2, refunded) | Account active |
| 3 | **Billing -> Credits**: are credits shown? | **If NO credits: stop. Go to Oracle (fallback).** |
| 4 | Do the onboarding tasks that add credits (VERIFY the list) | Credits balance recorded in `progress.md` |
| 5 | Root user: turn on **MFA** (authenticator app) | MFA active; write the sign-up date (6-month clock starts) |
| 6 | Create a daily **IAM user** with console access + MFA, **no access keys**; then stop using root | You log in as the IAM user |
| 7 | **AWS Budgets**: a monthly budget with email alerts (for example at $5, $10, $20) | Test email received |
| 8 | Pick the region (C0) and stay in it | Region shown in the top bar |

**Not allowed:** Organizations, Control Tower, IAM Identity Center (they can switch you to
paid). This overrides the older 7.11 text that suggested Identity Center.

## C2. Terraform without keys: AWS CloudShell

- **CloudShell** is a free terminal inside the AWS console, already logged in as you (no
  access keys on the laptop). Install the pinned Terraform version there (VERIFY install
  method and CloudShell limits: about 1 GB home folder).
- Optional 15-minute warm-up (learning): `init`, `plan`, `apply`, `destroy` on one tiny
  tagged S3 bucket, to see the whole cycle before the real thing.

## C3. Terraform: the infrastructure (`infra/aws/`)

Simplified on purpose for the deadline: the **default VPC** (exists in every account, free),
no custom network yet (custom VPC = Stage D).

| File | Creates | Why |
|---|---|---|
| `versions.tf` | Pins the Terraform and AWS provider versions (VERIFY) | Same result every time |
| `variables.tf` | region, instance type, domain, your email, GitHub image name | Nothing hard-coded |
| `security.tf` | Security group: **in** 80 + 443 from anywhere; **no 22**; out: all | Only web traffic gets in |
| `iam.tf` | Instance role: SSM Session Manager core policy; read ONE parameter path `/docpilot/*`; read ONE bucket | Least privilege: the server can do almost nothing else |
| `storage.tf` | Private S3 bucket for the seed snapshot (versioning on, public access blocked) | The main library index travels safely |
| `compute.tf` | `t3.small`, Ubuntu 24.04 LTS (VERIFY AMI lookup), gp3 20 GB, the role, `user_data` = `infra/aws/cloud-init.sh`; an **Elastic IP** | The IP never changes, so DuckDNS stays correct |
| `outputs.tf` | public IP, instance id, bucket name | You copy them into the next steps |

Every resource tagged `project=docpilot`. Order: `terraform plan` -> read every line with
me -> `apply`. **Done when:** `terraform plan` says "No changes", and the console shows
only `project=docpilot` resources.

**`cloud-init.sh` (runs once, on the first boot):**
1. Install Docker + the Compose plugin (VERIFY official install steps for Ubuntu 24.04).
2. Create a **2 GB swap file** (the safety net).
3. Write `docker-compose.prod.yml` and the `Caddyfile` to `/opt/docpilot/`.
4. Read the Groq key from **SSM Parameter Store** and write `/opt/docpilot/.env`
   (readable by root only).
5. `docker compose pull` + `up -d`; the app restores the seed index from S3 on first start.

## C4. Secrets and seed data (once)

| What | Where | How |
|---|---|---|
| `GROQ_API_KEY`, `LLM_MODEL`, `LLM_PROVIDER` | SSM Parameter Store, `/docpilot/...`, **SecureString** (standard tier; VERIFY it is free) | Console or CloudShell; never in git, never in the image, never in Terraform files |
| Seed snapshot of `docpilot_v1_ft200` | the private S3 bucket | Made on the laptop (`store/snapshots.py`), uploaded with CloudShell's "Upload file" (no keys) |

## C5. First boot check (SSM Session Manager)

In the console: EC2 -> the instance -> **Connect -> Session Manager**. Then:

```bash
sudo docker ps                       # caddy, app, qdrant: all "healthy"
free -h                              # RAM and swap in use
curl -s localhost:8000/ready         # {"status": "ready"}
sudo docker stats --no-stream        # record the numbers on the real server
```

## C6. The name and HTTPS

1. On duckdns.org (free, log in with GitHub): create `docpilot` (or another free name)
   and point it at the Elastic IP.
2. Caddy sees the domain, asks Let's Encrypt for a certificate, and serves HTTPS
   (automatic; renews by itself).
3. **Done when:** `https://<name>.duckdns.org` shows the padlock and the app.

## C7. Monitoring you get for free

| Tool | Watches | Tells you |
|---|---|---|
| UptimeRobot (free; VERIFY plan limits) | `https://<name>.duckdns.org/ready` every 5 minutes | Email when down and when back |
| AWS Budgets | Credit spending | Email at the thresholds from C1 |
| EC2 status checks + CloudWatch basic metrics | The server itself | CPU graph; "status check failed" |
| `docker` `restart: always` | Crashes | Restarts the container within seconds |
| **Prometheus + Grafana on your laptop** | The LIVE server's `/metrics` over HTTPS (protected by a secret token, so strangers cannot read it) | The same dashboard as B7, now with real public traffic, whenever your laptop is on |

Honest limit: laptop monitoring works only while the laptop runs. 24/7 dashboards (Grafana
Cloud free tier, VERIFY limits, or a bigger server) = Stage D.

## C8. Launch checklist (the live link)

| Check | How |
|---|---|
| Opens on **your phone** over mobile data (not home Wi-Fi) | Real outside access |
| A question about FastAPI gets a cited answer, streamed | The core works |
| Upload a small PDF in a new chat; ask about it | Uploads + background indexing work |
| A second browser cannot see the first browser's chat | A1 privacy |
| "Ignore all previous instructions…" is blocked | Guardrails in production |
| The 11th question in one minute is refused politely | A2 limits |
| Reboot the instance from the console; the link comes back by itself | Survives restarts |
| Billing page: only expected spending | Money safety |

Then: add the link to the README, record the real numbers (first answer time from your
phone, RAM on the server), write decision **D-062** with the facts, and tag `live-v1`.

## C9. How to update the live app later (manual for now)

1. Merge a PR to `main` -> CI green -> `image.yml` pushes a new image to GHCR.
2. Session Manager on the server: `cd /opt/docpilot && sudo docker compose pull && sudo docker compose up -d`.
3. Check `/ready`. Automatic deploys with GitHub OIDC = Stage D.

## C10. How to stop spending (keep this ready)

| Situation | Action |
|---|---|
| Pause for a while | Stop the instance (the Elastic IP still costs about $3.6/month: release it if pausing long) |
| Remove everything | `terraform destroy` in CloudShell, then check the EC2, S3 and Billing pages |
| Month 5 | Start the Oracle move (D-018); destroy AWS after the Oracle link works |

---

# Stage D: after submission (the rest of the production plan)

In the order of `phase_7_production.md` ... `4_phase_7_production.md`, now on a running system:

| Step | What | Why it matters |
|---|---|---|
| 7.10 + OIDC | GitHub Actions deploys automatically, with **no AWS keys** (OIDC role) | Merge = deploy |
| 7.6 (24/7) | Prometheus + Grafana always on (Grafana Cloud free tier or a bigger server), alerts | Watch the system even when the laptop is off |
| 7.16 (full) | Bigger load test against the live server | Real limits of the 2 GB server |
| 7.1-7.3 | Structured logs, API keys / accounts, Redis rate limits + cache | Real users, real limits |
| 7.4 | LLM fallback (second free provider), then LiteLLM | Groq down != DocPilot down |
| 7.5, 7.7 | Tracing, RAG quality monitoring | See bad answers in production |
| 7.12 (full) | Custom VPC, S3 Terraform state backend, CloudWatch logs | The "proper" infrastructure |
| 7.14 | k3s on the same server | Kubernetes for real |
| 7.15 | EKS exercise: plan only (it is never free) | Know what EKS needs |
| 7.17 | Incremental ingestion | Update the library without a full rebuild |
| 7.18 | **Oracle move** (before credits end) | The link lives on, free forever |

---

# Risks and what we do

| Risk | Plan |
|---|---|
| AISPL account has no credits | Launch nothing; Oracle fallback |
| 2 GB is not enough (B6 shows it) | Decide with numbers: larger type (more credit burn) or Oracle |
| Groq quota used up by visitors | A2 limits + "busy" message; Stage D adds a second provider |
| Someone uploads junk or huge files | A2 limits, A6 auto-cleanup, file checks (type, size, pages) |
| Prompt injection from the public | Phase 6 guards are in every path (2/18 -> 0/18 on the red team) |
| A deploy breaks the app | Pin image tags; roll back by pulling the previous `sha-` tag |
| Free-plan rules change | Weekly Billing check; budget emails |
| Server lost | Everything is code (Terraform + image + seed snapshot): rebuild in minutes; demo chats are disposable |

---

# Step checklist (tick as we go)

| Step | Status |
|---|---|
| Primer: public-app safety | not started |
| A1 Private chats per visitor | done 2026-10-23 (313 tests; two-browser check passed) |
| A2 Abuse limits | built 2026-10-23 from measured tokens (322 tests); values changed from the plan, see D-063; live check skipped by the learner |
| A3 Concurrency cap + A4 busy message | built 2026-10-23 (326 tests: full queue, fake 429, seat freed) |
| A5 uploads on disk + A6 cleanup + A7 /ready | done 2026-10-23 (332 tests; A5 on Docker Qdrant; A7 checked live) |
| B1 `.dockerignore` + B2 Dockerfile | done 2026-10-23 (D-064); 1.86 GB; offline start + no .env checked |
| B3 compose.prod + Caddyfile | built 2026-10-23 (D-065); configs validated; laptop run pending |
| A2 Abuse limits | not started |
| A3 Concurrency cap | not started |
| A4 "Busy" message | not started |
| A5 Upload vectors on disk | not started |
| A6 Auto-cleanup | not started |
| A7 `/ready` | not started |
| Primers: Docker images, HTTPS/DNS/Caddy, CI/CD + GHCR | not started |
| B1-B2 `.dockerignore`, `Dockerfile` | not started |
| B3 Production Compose + Caddy | not started |
| B4 Seed index | not started |
| B5 Image workflow to GHCR | not started |
| B6 Measure on the laptop (Linux containers) | not started |
| B7 `/metrics` + Prometheus + Grafana + load test (laptop) | not started |
| Primer: AWS part 3 (free plan, CloudShell, SSM, our setup) + Terraform update | not started |
| C1 AWS account (you) | not started |
| C2 CloudShell + Terraform | not started |
| C3 Terraform infrastructure | not started |
| C4 Secrets + seed snapshot | not started |
| C5 First boot check | not started |
| C6 DuckDNS + HTTPS | not started |
| C7 Monitoring | not started |
| C8 Launch checklist -> **live link** | not started |

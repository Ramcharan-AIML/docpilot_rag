Continues from [phase_7_production.md](phase_7_production.md)

# Teaching Notes, Phase 7: Production (Part 2 of 2)

---

## 9. Observability: logs, metrics, traces

For AI-specific monitoring (retrieval scores, sampled groundedness, refusal rate, topic
drift) read `primer_rag_monitoring.md`; for experiment tracking vs tracing read
`primer_mlflow.md` section 5.

**Like I'm five:** a car dashboard. **Logs** are the trip diary ("10:02 turned left").
**Metrics** are the gauges (speed, fuel, temperature over time). **Traces** are a dashcam
recording of one specific trip, step by step.

| Signal | Answers | Our tool |
|---|---|---|
| Logs | "What happened in request X?" | JSON lines to stdout, with `request_id` |
| Metrics | "How is the system doing overall, over time?" | Prometheus + Grafana |
| Traces | "Why was **this** request slow / wrong?" | Langfuse or Phoenix (D-009) |

**Structured (JSON) logs:** machines can filter `request_id = abc` or `status = blocked`.
Free-text logs need guesswork.

**Prometheus pull model:** our API exposes `/metrics` (plain text counters). Prometheus
visits it every 15 seconds and stores the time series. Grafana draws charts from
Prometheus.

**Metric types:**
- **Counter:** only goes up (requests, errors, cache hits).
- **Gauge:** goes up and down (review queue size).
- **Histogram:** counts values in buckets, so you can compute p50/p95 latency.

**Percentiles:** p50 = half of requests were faster than this. p95 = 95% were faster;
the slowest 5% are slower. Averages hide pain; p95 shows what unlucky users feel.

**Cardinality trap:** each unique label combination is a new time series. Putting
`request_id` or question text in a label creates millions of series and crashes
Prometheus. Labels must have few possible values.

**Tracing choice (D-009):** Langfuse self-hosted needs several services (heavy for a free
VM); Langfuse Cloud has a free tier with limits; Phoenix is lighter to self-host. We check
current docs and the VM's RAM, then decide.

---

## 10. Docker images for Python AI apps

**Multi-stage build:** stage 1 has compilers and builds wheels; stage 2 copies only the
results. Final image is smaller and has no build tools (less attack surface).

**Layer caching:** Docker reuses unchanged layers. Copy `requirements.txt` and install
**before** copying source code, so a code change does not reinstall every package.

**Non-root user:** if an attacker breaks into the app, they are not root inside the
container.

**Bake models into the image:** otherwise every container start downloads hundreds of MB
from Hugging Face, slow and fragile (if Hugging Face is down, you cannot start).

**CPU-only torch:** the default torch install can include large GPU libraries. Installing
the CPU build can shrink the image a lot (VERIFY the method; record sizes).

**`.dockerignore`:** like `.gitignore` for the build. Keeps `.env`, `.git`, data, and caches
out of the image.

**Health check:** Docker asks `/health` every 30 s; unhealthy containers can be restarted,
and Compose can wait for dependencies to be healthy before starting the API.

---

## 11. Docker Compose for the whole stack

One YAML file describes every service, its image, volumes, environment, health check, and
restart policy. `docker compose up -d` starts everything in the right order on a private
network where services find each other by name (`qdrant:6333`, `redis:6379`).

**Only Caddy is public.** Databases never get public ports. This one rule prevents a large
share of real-world data leaks.

**Volumes:** Qdrant data, Postgres data, Grafana settings survive container rebuilds.
Containers are cattle (replaceable); volumes are the farm (keep safe, back up).

---

## 12. CI/CD with GitHub Actions

**Like I'm five:** a robot inspector at the factory door. Every time you change something,
the robot runs the checklist. If anything fails, the change does not ship.

- **CI (continuous integration):** on every push/PR: lint, format check, tests, 500-line
  rule, dependency audit, **retrieval eval gate**.
- **CD (continuous delivery/deployment):** after CI passes on `main`: build the images
  (amd64 + arm64), push to AWS ECR (+ GHCR), deploy to the EC2 server through AWS SSM,
  smoke-test.
- **No AWS keys in GitHub:** the workflow uses **OIDC**: GitHub proves who it is and AWS
  hands back credentials that expire within the hour (see `primer_aws.md` section 4).

**The eval gate is what makes this project special.** Most portfolios test code. Ours tests
**AI quality**: if a change drops Recall@5 or MRR below `baseline - tolerance`, the build
fails. It uses only deterministic retrieval metrics, so it is free and reliable (D-011).
**Proving** it works (a deliberate bad PR that fails) is the screenshot interviewers remember.

**Why a tolerance:** tiny noise (e.g. a library update changing float rounding) should not
block every PR. The tolerance is a setting with a recorded reason.

**Secrets in CI:** only the judge-LLM keys live in GitHub Secrets (injected as environment
variables, never printed). App secrets live in AWS SSM Parameter Store. Pull requests from
forks do not get secrets (a security feature).

**The eval gate starts early:** CI `test` from Phase 1, `eval-gate` from Phase 2, and branch
protection makes them required (`primer_git_workflow.md`).

**Building for ARM:** GitHub's standard runners are x86. Buildx with QEMU emulation can build
`arm64` images (slower). Check whether native ARM runners are available for public repos
(VERIFY).

---

## 13. Cloud deployment and HTTPS

**AWS first (Phase 7), Oracle later (before month 6 of the AWS free plan).** Everything is
created by **Terraform**, and production runs on **k3s** on one EC2 instance. The full
explanations live in `primer_aws.md`, `primer_terraform.md`, and `primer_kubernetes.md`.

**Oracle trap for later:** ports must be opened in **both** the cloud security list **and**
the VM's own firewall. On AWS the security group is the only firewall we configure.

**HTTPS:** encrypts traffic so keys and questions cannot be read on the way. Certificates
come free from Let's Encrypt. **Caddy** requests and renews them automatically; Nginx
needs certbot setup. **DuckDNS** gives a free subdomain pointing to your VM's IP.

**Reverse proxy:** Caddy receives all traffic on 443 and forwards to the right internal
service (`api:8000`, `grafana:3000`). One public door, many rooms. On k3s, the **ingress
controller** plays this role (same idea, Kubernetes style).

**Last-resort fallback:** a Cloudflare Tunnel publishes a service running on your laptop
without opening ports. Same Compose stack, different host.

**Rollback:** every image is tagged with the git commit. Rolling back = deploying the
previous tag (`kubectl rollout undo` on k3s). Keep the command in the README.

---

## 14. Load testing

**Like I'm five:** before opening day, invite 50 friends to the restaurant at once and see
where it breaks.

Locust (Python) simulates users. We measure p50/p95 latency, error rate, 429 rate, and
fallback behaviour under load. Careful: real LLM calls under load burn free quota, so the
full-path test uses few users or a mock/local LLM. Report the VM size with the numbers:
latency without hardware context means nothing.

---

## 15. Incremental ingestion

Re-embedding everything on every docs update wastes time. We store a hash per document;
unchanged hash -> skip; changed -> delete that document's points, re-chunk, re-embed,
upsert; removed document -> delete its points. Bump cache versions so stale answers expire.

---

## 16. How you would scale it (interview question)

Stateless API workers behind a load balancer (state lives in Redis/Postgres/Qdrant);
a Qdrant cluster or managed Qdrant; a queue (e.g. a job worker) for ingestion; a GPU or
hosted reranker when latency matters; more caching; paid LLMs with higher limits if the
budget allows; on AWS: private subnets, a load balancer, multiple AZs, managed databases, and
possibly EKS when one node is no longer enough. Say what you would **measure** before each step.

---

## 17. Self-check (part 2)

1. Logs vs metrics vs traces: which answers "why was this request slow"?
2. What is p95 and why prefer it to the average?
3. What is the Prometheus cardinality trap?
4. Explain multi-stage builds, layer caching, and non-root users.
5. Why is only Caddy exposed?
6. What does your CI eval gate check, and how did you prove it works?
7. How does Caddy (or the k3s ingress) get certificates? Why OIDC instead of AWS keys in CI?
7b. Name the Oracle firewall trap for the later move.
8. How would you scale DocPilot to 1,000 users? What would you measure first?

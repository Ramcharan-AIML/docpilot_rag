# Phase 7 live link (part 2): Stage D and the checklist

Continues [5_phase_7_live_link.md](5_phase_7_live_link.md).

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
| B3 compose.prod + Caddyfile | done 2026-10-24 (D-065); ran on the laptop through Caddy |
| UI: demo library panel + switch + lock (learner request) | done 2026-10-24 (D-066) |
| B4 seed index (public snapshot, interview notes left out) | done 2026-10-24 (D-066): 413 chunks restored, /ready ready |
| B5 image.yml -> GHCR | DONE 2026-10-24 (D-067): run 1 failed (detached HEAD), fixed; run 2 success 3 min 33 s; package public; pull OK, 1.86 GB |
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
| B5 Image workflow to GHCR | DONE 2026-10-24 |
| B6 Measure on the laptop (Linux containers) | DONE 2026-10-24 (D-068) |
| B7 `/metrics` + Prometheus + Grafana + load test (laptop) | not started |
| Primer: AWS part 3 (free plan, CloudShell, SSM, our setup) + Terraform update | not started |
| C1 AWS account (you) | DONE 2026-10-24: Free plan, $100, project tied to Sydney (D-069) |
| C2 CloudShell + Terraform | not started |
| C3 Terraform infrastructure | not started |
| C4 Secrets + seed snapshot | not started |
| C5 First boot check | not started |
| C6 DuckDNS + HTTPS | not started |
| C7 Monitoring | not started |
| C8 Launch checklist -> **live link** | not started |

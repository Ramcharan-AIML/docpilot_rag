Continues from [2_architecture.md](2_architecture.md)

# DocPilot Architecture (Part 3 of 3): Cloud, Infrastructure, MLOps

Part 3 describes **where DocPilot runs and how changes reach it**: environments, the AWS
design, IAM and secrets, storage, Kubernetes, CI/CD, Terraform, the MLOps loop, portability
to Oracle, and cost controls. Decisions D-017 to D-025. Teaching: the `teaching/primer_*.md`
files.

---

## 19. Environments

| Environment | Where | Runs | Purpose | Phase |
|---|---|---|---|---|
| **Local dev** | your laptop | Python venv + Docker Compose (Qdrant, SeaweedFS, MLflow; later the full stack) | build, test, experiment | 1-7 |
| **CI** | GitHub-hosted runners | tests, fixture-corpus eval gate, terraform validate, image builds | protect `main` | 1-7 |
| **Production (AWS)** | one EC2 instance, k3s | api, Qdrant, Redis, Postgres, Prometheus, Grafana | public demo for ~5 months | 7 |
| **EKS exercise** | AWS EKS | same manifests | learn managed Kubernetes; **destroyed same session** | 7 |
| **Production (Oracle)** | one A1 VM, k3s | same as AWS production | long-term free home | month 5+ |

Same container images and the same Kubernetes manifests in every Kubernetes environment.
Only infrastructure code (Terraform module) and image architecture differ.

---

## 20. AWS network design

```text
Region (one, chosen in 7.11)
└── VPC 10.0.0.0/16                         tags: project=docpilot
    ├── Internet gateway
    ├── Route table: 0.0.0.0/0 -> internet gateway
    └── Public subnet 10.0.1.0/24 (one AZ)
        └── EC2 instance (k3s node)
            ├── Security group "docpilot-app"
            │     inbound : 443/tcp from 0.0.0.0/0, 80/tcp from 0.0.0.0/0
            │     outbound: all (LLM APIs, ECR, S3, SSM, CloudWatch)
            │     NOT open: 22 (SSH), 6333 (Qdrant), 6379 (Redis), 5432 (Postgres), 3000, 9090
            ├── Instance profile -> role "docpilot-ec2"
            └── gp3 root volume (k3s local-path PVCs live here)
```

**Why this shape:** one node, no NAT gateway (hourly + per-GB charges), no load balancer
(hourly charge). Databases are reachable only inside the node. At larger scale: private
subnets for data, an Application Load Balancer, multiple AZs, managed databases.

---

## 21. Identities, roles, and trust

```text
GitHub Actions (repo X, branch main)
    │ OIDC token ("I am repo X, ref main")
    ▼
IAM OIDC provider (token.actions.githubusercontent.com) ──trusts──▶ role "docpilot-gha-deploy"
                                                                   allowed: ecr push (one repo),
                                                                            ssm:SendCommand (one instance)
EC2 instance ──wears──▶ role "docpilot-ec2"
                        allowed: ecr pull (one repo), s3 read/write (two buckets),
                                 ssm managed instance, cloudwatch agent, read SSM parameters /docpilot/*
You (daily admin, MFA) ──▶ console / CLI with short-lived login
Root user ──▶ MFA, locked away
```

No long-lived AWS access keys exist anywhere in this design.

---

## 22. Secrets flow

| Secret | Stored in | Delivered to |
|---|---|---|
| LLM API keys, Postgres password, Grafana admin, API-key salt | SSM Parameter Store (SecureString) `/docpilot/*` | `deploy.sh` reads them with the instance role -> creates the Kubernetes Secret |
| Judge LLM keys for nightly evals | GitHub Secrets | `eval.yml` environment only |
| Local development values | `.env` (gitignored) | Compose and scripts |
| AWS credentials | **nowhere** (roles + OIDC) | n/a |

Never: in git, in images, in Terraform variables committed to git, in logs.

---

## 23. Data and storage map

| Data | Lives in (AWS) | Lives in (local) | Backup / restore |
|---|---|---|---|
| Vectors + payloads | Qdrant on a PVC | Qdrant volume | snapshot -> S3 `docpilot-snapshots` (after each ingest) |
| Checkpoints, review queue, API keys, ingest manifest | Postgres on a PVC | Postgres volume | `pg_dump` -> S3 (scheduled CronJob) |
| Cache, rate-limit counters | Redis (memory) | Redis | none needed (rebuildable) |
| Raw docs | S3 `docpilot-raw-docs` | SeaweedFS bucket | re-download script |
| Container images | ECR (+ GHCR mirror) | local Docker | rebuild from git SHA |
| Terraform state | S3 `docpilot-tfstate` (versioned) | local file for warm-up | S3 versioning |
| Eval runs | MLflow on the laptop (SQLite + SeaweedFS artifacts) and results JSON in git | same | git |
| Metrics history | Prometheus volume (short retention) | same | not backed up (operational data) |

---

## 24. Kubernetes layout (k3s, namespace `docpilot`)

| Object | Kind | Notes |
|---|---|---|
| `api` | Deployment (1 replica) + Service | probes `/health`, `/ready`; requests/limits from measurements |
| `qdrant` | StatefulSet + Service + PVC | not exposed outside the cluster |
| `postgres` | StatefulSet + Service + PVC | not exposed |
| `redis` | Deployment + Service | `maxmemory` set |
| `prometheus`, `grafana` | Deployments + PVCs | Grafana exposed via ingress with password |
| `docpilot-config` | ConfigMap | non-secret settings |
| `docpilot-secrets` | Secret | created by `deploy.sh`, never committed |
| `ingress` | Ingress | `docpilot.<domain>` -> api; `grafana.<domain>` -> grafana; TLS via Let's Encrypt |
| `ingest` | CronJob | incremental ingestion + snapshot to S3 |
| `pg-backup` | CronJob | `pg_dump` to S3 |
| `groundedness-sampler`, `drift-job` | CronJobs | RAG monitoring jobs |

**Resource budget** (filled from real `kubectl top` measurements; `n/a` until measured):

| Component | RAM request | RAM limit |
|---|---|---|
| k3s itself | n/a | n/a |
| api | n/a | n/a |
| qdrant | n/a | n/a |
| others | n/a | n/a |
| **Total vs instance RAM** | n/a | n/a |

---

## 25. Change pipeline: from a keystroke to production

```text
feat/* branch ─PR─▶ phase branch ─PR (at gate)─▶ main
   │                    │                          │
   CI: test, eval-gate  CI: test, eval-gate,       deploy.yml:
                        audit, terraform-check       OIDC -> buildx amd64+arm64 -> ECR + GHCR
                                                     -> SSM: deploy.sh <sha>
                                                     -> kubectl set image + rollout status
                                                     -> on failure: rollout undo
                                                     -> smoke test https://<host>/ready
tags: phase-N on main after each gate
infra changes: PR shows `terraform plan` output (pasted or via CI) -> apply by hand after merge
```

Infrastructure is **applied by you**, not by CI, in this project: fewer powerful credentials
in CI, and you read every plan. (Teams often automate this with extra safeguards.)

---

## 26. Terraform structure and state

```text
infra/
├── bootstrap/            cloud-init.sh, deploy.sh       (shared by AWS and Oracle)
├── bootstrap_state/      S3 state bucket                 (local state, applied once)
├── warmup/               Docker provider exercise        (local state)
├── modules/aws_app_host/ network, security, iam, compute, storage, monitoring
├── modules/oracle_app_host/  vcn, security list, A1 VM, bucket
├── envs/aws/             backend "s3", module aws_app_host
├── envs/oracle/          backend (VERIFY Oracle option), module oracle_app_host
└── eks_exercise/         separate root; plan-only by default
```

State: S3 bucket, versioning on, locking enabled (VERIFY current mechanism), never in git.

---

## 27. The MLOps loop

```text
        ┌──────────────── offline ────────────────┐      ┌──────────── online ─────────────┐
        │ golden set ─▶ eval runs ─▶ MLflow ─▶     │      │ users ─▶ traces + RAG metrics ─▶ │
        │ ABLATION.md ─▶ decision log              │      │ Grafana alerts                   │
        └──────────────▲──────────────┬───────────┘      └──────────────┬───────────────────┘
                       │              │ CI eval gate protects main      │
                       │              ▼                                 │
                       │        deploy (CD) ─────────────────────────────┘
                       │                                                │
                       └──── reviewed questions from traces / HITL ◀────┘
```

Evals decide what ships; the gate stops regressions; monitoring finds new problems on real
traffic; those problems become new golden questions. MLflow is the offline notebook; tracing
and Prometheus are the online eyes.

---

## 28. Portability: AWS to Oracle

| Layer | Same on both? |
|---|---|
| App code, images (multi-arch), Kubernetes manifests | yes |
| `cloud-init.sh`, `deploy.sh` | yes (cloud-specific bits behind small `if` blocks, documented) |
| Terraform modules | no: `aws_app_host` vs `oracle_app_host`, same outputs |
| Secrets store | no: SSM Parameter Store vs Oracle's option (VERIFY) |
| Deploy trigger | no: SSM on AWS; another method on Oracle (decision at 7.18) |
| Object storage | S3 vs Oracle Object Storage (S3-compatible API, VERIFY) or SeaweedFS on the VM; same boto3 code with a different endpoint |
| Machine monitoring | CloudWatch on AWS only; Prometheus/Grafana on both |

---

## 29. Cost architecture

| Spends AWS credits | Control |
|---|---|
| EC2 instance hours | right-size from measurements; stop when not needed |
| EBS volume, snapshots | size from need; lifecycle on old snapshots |
| Public IPv4 address (USD 0.005/hour, checked 2026-10-08) | one only |
| S3 storage and requests | lifecycle rules; small data |
| ECR storage | lifecycle policy: keep last N images |
| CloudWatch logs, alarms | 7-day retention; few alarms |
| EKS (USD 0.10/hour control plane, checked 2026-10-08) | plan-only default; destroy same session |
| **Not used** | NAT gateway, load balancer, managed databases |

Budget alerts at 25/50/75/90% of credits. Weekly review routine in `teaching/2_primer_aws.md`.

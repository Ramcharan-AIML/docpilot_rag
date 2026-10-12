Continues from [phase_7_interview.md](phase_7_interview.md)

# Interview Questions, Phase 7 (Part 2): AWS, Terraform, Kubernetes, Monitoring, MLOps

Numbers in brackets like `[n/a]` are filled from your real runs only.

---

### Q1. "Walk me through your AWS architecture."

**Model answer:** "One region, one VPC with a public subnet and an internet gateway. A single
EC2 instance, `m7i-flex.large` [confirm], runs k3s. Its security group allows only 80 and 443;
there is no SSH port: I connect with SSM Session Manager. The instance wears an IAM role that
can pull from one ECR repository, read and write two S3 buckets, and send logs to CloudWatch.
GitHub Actions deploys with an OIDC role, so there are no AWS keys anywhere. S3 holds raw docs,
Qdrant snapshots, and Terraform state. CloudWatch watches the machine; Prometheus and Grafana
watch the app. Budgets alert me at 25/50/75/90% of credits. Everything is created by Terraform."

**Follow-up:** "Why no private subnets?" "A NAT gateway or load balancer is billed hourly and
would eat the free-plan credits. With one node, a tight security group and no SSH give the
protection I need. At scale I would put data in private subnets behind a load balancer."

---

### Q2. "How do you avoid leaking AWS credentials?"

**Model answer:** "There are none to leak. CI uses GitHub OIDC: GitHub proves the workflow's
identity and AWS returns credentials that expire within the hour, trusted only for my repo's
`main` branch. The server uses an instance role. App secrets live in SSM Parameter Store and
are turned into a Kubernetes Secret at deploy time. My own login is short-lived with MFA; the
root user is locked away."

---

### Q3. "Why Terraform? What is state?"

**Model answer:** "Infrastructure as code: repeatable, reviewable in PRs, and destroyable,
which matters on a credit budget. State is Terraform's record of what it created and the real
ids; I keep it in a versioned S3 bucket with locking, never in git. I read every `plan` before
`apply`, especially any destroy line. My CI runs `terraform fmt -check` and `validate`."

**Follow-up:** "Terraform's licence?" "BSL since 2023, free for managing my own infra.
OpenTofu is the open-source fork; my HCL runs on both."

---

### Q4. "You say your infrastructure is portable. Prove it."

**Model answer:** "Terraform resources are provider-specific, so portability comes from
structure: one module per cloud (`aws_app_host`, `oracle_app_host`) with identical outputs,
one shared `cloud-init.sh`, multi-arch images (amd64 for AWS, arm64 for Oracle), and the same
Kubernetes manifests. Before the AWS free plan ended I moved the demo to Oracle: snapshot to
object storage, apply the Oracle env, restore, switch DNS, destroy AWS. It took [n/a] hours."

---

### Q5. "Why k3s and not EKS?"

**Model answer:** "One node and a small budget. k3s is certified Kubernetes in one binary;
its docs list 2 GB RAM for a server node, which fit on my instance after measuring. EKS
charges for the control plane every hour, even idle. I did the EKS exercise with Terraform:
I read the plan [and applied, deployed the same manifests, and destroyed it in the same
session; the bill was n/a]. I would choose EKS when there are multiple nodes, a team, and
uptime requirements that justify a managed control plane."

---

### Q6. "Explain your Kubernetes objects."

**Model answer:** "The API is a Deployment with a Service, liveness probe on `/health` and
readiness probe on `/ready`, and requests/limits from measured usage. Qdrant and Postgres
are StatefulSets with PVCs. Config is a ConfigMap; secrets a Secret created at deploy time.
An Ingress routes the domain with Let's Encrypt certificates. CronJobs run incremental
ingestion, Postgres backups to S3, and the RAG monitoring jobs. A deploy is `kubectl set
image` plus `rollout status`; if the new pod never becomes ready, traffic stays on the old
one and the script runs `rollout undo`."

**Follow-up:** "Liveness vs readiness?" "Liveness failing restarts the pod; readiness failing
removes it from the Service so it gets no traffic."

---

### Q7. "What do you monitor for a RAG system in production?"

**Model answer:** "Beyond latency and errors: retrieval top-score distribution, relevant-chunk
counts, refusal rate, guard blocks by reason, fallbacks, cache hit rate, review-queue size,
sampled groundedness (about 5% of answers judged by the same judge as my offline evals), and
topic drift (distance between recent questions and the corpus, plus out-of-scope share). AI
systems fail quietly with 200 OK, so these are my warning lights. Alert thresholds came from
a week of real traffic: [n/a]."

---

### Q8. "MLflow vs Langfuse: why both?"

**Model answer:** "Different questions. MLflow is my lab notebook for offline experiments:
each eval run logs params, metrics, and results, and my ablation table is generated from it.
Tracing records one live request step by step: which chunks, which LLM calls, how long each
node took. One tells me which recipe is best on average; the other why request 42 failed.
[If you chose MLflow tracing for D-009: MLflow 3 can also trace, so I used one tool for both.]"

---

### Q9. "Describe your Git workflow."

**Model answer:** "Feature branches per step, merged into the phase branch by squash PRs;
the phase branch reaches `main` by a PR at the gate with a merge commit; an annotated tag per
phase. `main` is protected: PRs only, and the `test`, `eval-gate`, `audit`, and
`terraform-check` checks must pass. The eval gate runs retrieval evals on a fixture corpus I
wrote myself, so it is deterministic and free. I proved it by opening a PR that removed the
BGE query prefix: it failed [screenshot]."

---

### Q10. "Why did you use SeaweedFS instead of MinIO?"

**Model answer:** "MinIO's community edition was archived in 2026 and its images removed, so
running it meant unpatched software. My code talks the S3 API through boto3, so I swapped the
product, not the code: SeaweedFS locally, real S3 on AWS by changing only the endpoint. That
is the swappable-provider principle applied to storage."

---

### Q11. "How did you keep the AWS bill at zero?"

**Model answer:** "The free plan cannot bill beyond its credits, but I still treated credits as
a budget: account opened only in Phase 7, budget alerts, one region, everything tagged and
created by Terraform, no NAT gateway or load balancer, ECR lifecycle policy, 7-day log
retention, EKS destroyed in the same session, and a weekly check of Cost Explorer and EC2
Global View. Credits used by the end: [n/a]."

---

### Q12. Trap: "Isn't Kubernetes overkill for one server?"

**Model answer:** "For pure operations, Compose was enough, and I ran Compose first. I moved to
k3s on purpose: rolling updates gated by readiness probes, automatic restarts, CronJobs, and
the same manifests that run on EKS. It cost about [n/a] GB of RAM. I would not recommend
Kubernetes to a team with one small service unless they need those features or plan to grow."

Continues from [2_phase_7_production.md](2_phase_7_production.md)

# Phase 7: Production (Implementation Plan, Part 3 of 4): AWS, Terraform, Kubernetes

Part 3 covers the **cloud**: 7.11 to 7.15.
Teaching: `teaching/primer_aws.md` + `2_primer_aws.md`, `teaching/primer_terraform.md`,
`teaching/primer_kubernetes.md`. Decisions D-017 to D-023.

**Cost rule for this whole part (Rule 17):** read every `terraform plan`; tag everything
`project=docpilot`; one region; budget alerts on; nothing left running that you did not
mean to run. Free plan facts (checked 2026-10-08): USD 100 + up to 100 credits, 6 months,
suspension afterwards.

---

## Step 7.11: AWS account, safety, CLI, and a Terraform warm-up

**Order matters. Nothing gets created in AWS until items 1-5 are done.**

1. **Create the AWS account now** (start of Phase 7, decision D-017). Write the sign-up date
   in `decisions.md`: the 6-month clock starts today. Put a calendar reminder at **month 5**
   for the Oracle move (7.18).
2. Root user: MFA on; then stop using it.
3. Create your daily admin identity with MFA (VERIFY current recommended method: IAM Identity
   Center vs IAM user).
4. **AWS Budgets:** a budget equal to your credits with email alerts at 25/50/75/90%.
   Check the Billing / Free Tier page.
5. Install the AWS CLI v2 and Terraform (VERIFY versions; pin the Terraform version in
   `infra/.terraform-version` and `required_version`). Run `aws sts get-caller-identity`.
6. Pick the region (near you, offers the free-plan instance types: check with the
   `describe-instance-types --filters Name=free-tier-eligible,Values=true` command).
7. **Terraform warm-up, no cloud, no cost:** `infra/warmup/main.tf` uses the Docker provider
   (VERIFY) to create a Qdrant container on your laptop. Practise `init`, `plan`, `apply`,
   change the port and re-`plan` (see the `~`), `destroy`. Look inside `terraform.tfstate`
   once, then never edit it.
8. `.gitignore`: add `*.tfstate`, `*.tfstate.*`, `.terraform/`, `*.tfvars` (commit only
   `*.tfvars.example`), `crash.log`.

**Done when:** you can explain plan/apply/destroy/state from the warm-up, and the budget email
alert is configured.

---

## Step 7.12: Terraform for the AWS infrastructure

**Folder layout** (portable design, see the Terraform primer section 6):

```text
infra/
├── bootstrap/cloud-init.sh      # shared by AWS and Oracle: Docker, k3s later, deploy.sh
├── bootstrap/deploy.sh          # pull image tag, apply, wait for /ready, roll back on failure
├── bootstrap_state/main.tf      # one-time: S3 bucket for state (versioned, private)
├── modules/aws_app_host/
│   ├── network.tf               # VPC, public subnet, internet gateway, route table
│   ├── security.tf              # security group: 80, 443 in; all out; NO 22
│   ├── iam.tf                   # instance role (ECR pull, S3 buckets, SSM, CloudWatch agent)
│   │                            # + GitHub OIDC provider and deploy role (ECR push, SSM send)
│   ├── compute.tf               # EC2 instance, gp3 root disk, user_data = cloud-init.sh
│   ├── storage.tf               # S3 buckets (raw docs, snapshots); ECR repo + lifecycle policy
│   ├── monitoring.tf            # CloudWatch log group (7-day retention), alarms, SNS email
│   ├── variables.tf  outputs.tf
├── envs/aws/
│   ├── main.tf                  # backend "s3" + module "app" { source = "../../modules/aws_app_host" }
│   ├── terraform.tfvars.example # region, instance_type, your email for alarms, github repo
└── (oracle and eks_exercise come later)
```

**Build it in this order, `plan` + `apply` after each, reading every plan line:**

| # | What | Why this order |
|---|---|---|
| 1 | `bootstrap_state`: state bucket (versioning on, public access blocked) | everything else stores its state here |
| 2 | `network.tf` | nothing can exist without a network |
| 3 | `security.tf` | the firewall before the server |
| 4 | `iam.tf` | the server and CI need roles before they start |
| 5 | `storage.tf` | buckets and ECR exist before the first push |
| 6 | `monitoring.tf` | log group exists before the agent sends logs |
| 7 | `compute.tf` | the server last; it boots with cloud-init and finds everything ready |

**IAM least privilege (write each policy by hand, with comments):**

| Role | Allowed | Not allowed |
|---|---|---|
| EC2 instance role | pull from ECR repo `docpilot-api`; read/write the 2 DocPilot buckets; SSM managed instance; CloudWatch agent | anything else; no IAM changes; no other buckets |
| GitHub deploy role (OIDC) | push to ECR repo `docpilot-api`; `ssm:SendCommand` to **this** instance | trust only `repo:<you>/docpilot_rag:ref:refs/heads/main` (VERIFY the exact condition format) |

**Instance size:** use the RAM measured in 7.9. Among free-plan types `m7i-flex.large` has the
most memory (VERIFY specs). Disk: gp3, size from the measured need plus headroom.

**Outputs:** `public_ip`, `instance_id`, `ecr_repo_url`, `deploy_role_arn`. Copy them into
GitHub **Variables** (7.10.4).

**Done when:** `terraform plan` in `envs/aws` shows "No changes"; the AWS console shows only
resources tagged `project=docpilot`; CI's `terraform-check` job is green.

---

## Step 7.13: First deployment on EC2 (Docker Compose) + HTTPS

1. cloud-init has installed Docker and the CloudWatch agent (VERIFY agent config for Docker
   logs and memory/disk metrics).
2. Connect with `aws ssm start-session --target <instance-id>` (no SSH).
3. Copy secrets: put the `.env` values into **SSM Parameter Store (SecureString)** (VERIFY free
   usage; decision entry) and let `deploy.sh` write `.env` on the server from there. Never in
   git, never in the image, never in Terraform state as plain text.
4. Data: restore the Qdrant snapshot from S3 (made locally in 3.1b and uploaded to the AWS
   bucket), instead of re-embedding on the server.
5. DuckDNS: point your name at the EC2 public IP. Caddy fetches certificates.
6. Merge a small PR to `main`: watch `deploy.yml` build, push, deploy, smoke-test.
7. Check CloudWatch: logs arrive; the "status check failed" alarm exists; budget is calm.

**Done when:** `https://<name>.duckdns.org/ready` is green from your phone (not your laptop),
deployed by CI, with no SSH port and no stored AWS keys.

---

## Step 7.14: k3s on the same EC2 instance (production runs on Kubernetes)

Teaching: `primer_kubernetes.md`. Decision D-021.

1. cloud-init installs k3s (VERIFY install command and version pin). Check RAM after install:
   k3s docs (checked 2026-10-08) list 2 GB minimum for a server node.
2. **Manifests** in `deploy/k8s/` (one object type per file, each under 500 lines):
   `namespace.yaml`, `configmap.yaml`, `secret.example.yaml` (real secret created by
   `deploy.sh` from Parameter Store, never committed), `api-deployment.yaml`,
   `api-service.yaml`, `ingress.yaml`, `qdrant-statefulset.yaml`, `redis-deployment.yaml`,
   `postgres-statefulset.yaml`, `monitoring/` (Prometheus, Grafana), PVCs.
3. HTTPS: k3s's bundled ingress controller with Let's Encrypt (VERIFY: Traefik ACME vs
   cert-manager) replaces Caddy on the server. Caddy remains in the local Compose file.
4. Probes: liveness `/health`, readiness `/ready`. Requests/limits from measured usage.
5. `deploy.sh` switches to `kubectl set image deploy/api api=<repo>:<sha>` +
   `kubectl rollout status`; on failure `kubectl rollout undo`.
6. Migration on the same VM: stop Compose, apply manifests, restore data into the PVCs,
   switch DNS only if the IP changes (it does not; same VM).
7. Exercise: kill the api pod (`kubectl delete pod ...`) and watch it come back; deploy a bad
   image tag and watch the readiness probe stop traffic and the rollback work.

**Done when:** the public URL is served by k3s; a CI deploy performs a rolling update; the
two exercises in item 7 are recorded in `progress.md`.

---

## Step 7.15: EKS exercise (plan-only by default; never left running)

Decision D-023. Facts (checked 2026-10-08): EKS has **no free control plane**; it costs
USD 0.10 per cluster-hour plus nodes and networking, idle or not.

1. `infra/eks_exercise/`: a separate Terraform root using the community EKS module (VERIFY
   module source and version), its own small VPC, one small managed node group.
2. **Default:** `terraform init` + `terraform plan` only. Read the plan and write in
   `progress.md`: what EKS needs that k3s did not (IAM roles for the cluster and nodes,
   multiple subnets across AZs, add-ons, security groups).
3. **Optional apply** (only if credits allow; decide in writing first): set a 60-minute
   timer -> `apply` -> `aws eks update-kubeconfig` -> `kubectl apply -f deploy/k8s/` -> see it
   run -> **`terraform destroy`** -> check EC2 Global View, EKS console, and Billing show
   nothing left. Record the real cost from Billing the next day.
4. Never commit kubeconfig files; never leave the cluster overnight.

**Done when:** the plan is read and summarised (and, if applied, destroyed with the cost
recorded).

Continued in [4_phase_7_production.md](4_phase_7_production.md)

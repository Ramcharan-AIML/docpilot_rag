Continues from [primer_aws.md](primer_aws.md)

# Primer: AWS From Zero (Part 2 of 2)

---

## 10. How DocPilot uses everything together

```text
                       GitHub Actions
                 (lint, tests, eval gate, build)
                            │  OIDC role (no stored keys)
                            ▼
                    ┌──────────────┐
                    │ ECR          │  docpilot-api:<git-sha>  (lifecycle: keep last N)
                    └──────┬───────┘
                           │ pull (instance role)
 user ── HTTPS ──▶ ┌───────▼──────────────── VPC 10.0.0.0/16 ─────────────────────────┐
  (DuckDNS name)   │  public subnet                                                    │
                   │  ┌──────────────────────── EC2 (m7i-flex.large, VERIFY) ───────┐ │
                   │  │ security group: 80, 443 only. No SSH (Session Manager).      │ │
                   │  │ Caddy ─▶ api ─▶ qdrant, redis, postgres                       │ │
                   │  │          prometheus ─▶ grafana     (Compose first, then k3s) │ │
                   │  └───────┬──────────────────────────────┬───────────────────────┘ │
                   └──────────┼──────────────────────────────┼─────────────────────────┘
                              │ boto3 (instance role)        │ CloudWatch agent
                              ▼                              ▼
                     ┌────────────────┐             ┌──────────────────┐
                     │ S3 buckets     │             │ CloudWatch       │
                     │ raw docs,      │             │ logs, metrics,   │
                     │ snapshots,     │             │ alarms -> email  │
                     │ tf state       │             └──────────────────┘
                     └────────────────┘
 Everything above is created by Terraform (infra/), not by clicking.  Budget alerts on.
```

**One request, end to end:** DNS name -> EC2 public IP -> security group allows 443 ->
Caddy (HTTPS) -> API container -> Qdrant/Redis/Postgres on the same machine -> answer.
Background: CloudWatch watches the machine; Prometheus watches the app; S3 keeps backups.

---

## 11. Cost traps (read twice)

| Trap | Why it bites | Our protection |
|---|---|---|
| Forgetting resources in another region | You never look there | One region only; `project=docpilot` tags; Terraform knows everything it made |
| NAT gateway | charges every hour plus per GB | not used (public subnet design) |
| Idle EKS cluster | USD 0.10/hour for the control plane alone, even idle (checked 2026-10-08) | `terraform plan` only by default; if applied, destroy within the same session |
| Public IPv4 addresses | USD 0.005/hour each (checked 2026-10-08) | one address only |
| Stopped instance's disk and old snapshots | storage still billed | lifecycle rules; delete old snapshots |
| CloudWatch logs kept forever | log storage grows | 7-day retention |
| Big Docker images in ECR | storage grows with every push | ECR lifecycle policy |
| Running a big instance while not using it | hours burn credits | stop the instance when not demoing (data stays on EBS) |
| Free plan ends at 6 months | account suspended, then deleted | move to Oracle before month 6 (D-018) |

**Weekly routine (5 minutes):** open Billing -> credits remaining and forecast; Cost Explorer
-> which service costs most; EC2 Global View -> nothing running in other regions;
`terraform plan` -> shows "no changes" (nothing created by hand).

---

## 12. AWS CLI basics you will use

```powershell
aws --version
aws sso login                         # or another short-lived login method (VERIFY)
aws sts get-caller-identity           # "who am I logged in as?" -> always run this first
aws ec2 describe-instance-types --filters Name=free-tier-eligible,Values=true --query "InstanceTypes[*].InstanceType" --output text
aws s3 ls                             # list buckets
aws ecr describe-repositories
aws ssm start-session --target <instance-id>   # terminal on the server, no SSH
```

`aws sts get-caller-identity` first, every time: it prevents the "I deleted things in the
wrong account" disaster.

---

## 13. Moving to Oracle Cloud before the free plan ends (D-018)

| Piece | AWS (Phase 7) | Oracle Always Free (after) |
|---|---|---|
| Server | EC2 `m7i-flex.large` (x86) | Ampere A1 VM (ARM; VERIFY current allowance) |
| Network | VPC, subnet, security group | VCN, subnet, security list |
| Images | ECR (+ GHCR mirror) | GHCR |
| Object storage | S3 | Oracle Object Storage (has an S3-compatible API, VERIFY) or SeaweedFS on the VM |
| Infra code | `infra/envs/aws` | `infra/envs/oracle` (same structure, different provider) |
| First-boot script | shared `infra/bootstrap/cloud-init.sh` | same file |
| App layer | Compose / k3s manifests | identical |
| Monitoring | Prometheus + Grafana (+ CloudWatch) | Prometheus + Grafana |

What changes: the Terraform provider resources and the image architecture (amd64 -> arm64,
handled by multi-arch builds). What does not change: the app, the containers, the manifests,
the boot script. That split is the whole point of portable infrastructure.

**Migration checklist (month 5):** snapshot Qdrant to object storage -> `terraform apply` the
Oracle env -> restore snapshot -> point DuckDNS to the new IP -> verify `/ready` and run the
eval smoke test -> `terraform destroy` the AWS env -> confirm Billing shows nothing running.

---

## 14. Why AWS (and why not only Oracle, GCP, or Azure)

| Option | Notes |
|---|---|
| **AWS** | Most requested cloud in job descriptions; IAM, VPC, EC2, S3, ECR, CloudWatch are the vocabulary interviewers expect. Free plan gives 6 months of credits |
| Oracle Always Free | Free forever, generous ARM VM, but fewer employers ask for it. Our long-term home |
| GCP / Azure | Also good with their own credits; we pick one cloud to learn deeply rather than three shallowly |

---

## 15. Self-check

1. Region vs Availability Zone?
2. Five facts about the AWS free plan, and what happens at month 6?
3. Why lock away the root user? What do you use instead?
4. Role vs access key: why are roles safer? What is OIDC used for here?
5. Draw our VPC: what is open in the security group, and why is there no NAT gateway?
6. Stop vs terminate an instance?
7. CloudWatch vs Prometheus: what does each watch?
8. Name five cost traps and our protection for each.
9. What changes and what stays the same when we move to Oracle?

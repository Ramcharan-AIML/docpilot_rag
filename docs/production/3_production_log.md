# Production log (part 3)

Continues [2_production_log.md](2_production_log.md) (500-line rule). Same format:
one section per step, newest at the BOTTOM.

---

## Decision: Stage C (AWS) before B7 (Prometheus + Grafana) (2026-10-24)

**Mentor's advice (I agreed):** the live link is what I submit (~2026-10-25); monitoring is
added to a server that already works. B7 moves after the launch.

---

## Step C0: teach + facts checked before sign-up (2026-10-24)

**Teach first:** `06_teach_aws_live.md` (AWS in 6 things, the free plan, IAM root / user /
role, MFA, no access keys, regions, no port 22, Session Manager, Parameter Store,
Terraform, our setup, money safety, interview questions).

**Facts checked on official pages today:**
| Fact | Value |
|---|---|
| Credits | $100 at sign-up + up to $100 from activities |
| Free plan length | 6 months or until credits end; then the account CLOSES (no bill) |
| t3.small on the free plan | yes, for accounts created from 2025-07-15 |
| Public IPv4 | $0.005 / hour = $3.65 / month |
| t3.small Mumbai | about $0.0224 / hour (third-party list; confirm in the console) |
| India (AISPL) credits | NOT confirmed anywhere: check the Credits page right after sign-up |
| Terraform / AWS provider to pin | 1.16.5 / 6.68.0 (newest that are 2+ weeks old) |

**Big lesson:** on the free plan the risk is not a bill, it is the **link dying** (credits
end or month 6). So the Oracle move before month 6 is required, not optional.

**Next:** C1, I create the account (mentor guides), and in parallel a DuckDNS name.

---

## Step C1 part 1: AWS account created (2026-10-24) - credits CONFIRMED

| Check | Result |
|---|---|
| Plan | **Free** |
| Credits remaining | **$100.00** (so India / AISPL accounts DO get them: the open risk is closed) |
| Days remaining | **183** -> the free plan ends **2027-04-24** (Oracle move before that date) |
| Amount due | $0.00 ("No charges while on the free plan") |
| First region shown | `ap-southeast-2` (Sydney!) -> switched to **Mumbai `ap-south-1`** |

**Money maths:** about $22 / month x 6 months = about $132. $100 alone runs out around
month 4.5, so the extra credit activities (each about $20, e.g. launch an EC2 instance,
set up a budget) matter: they let the credits last the whole 6 months.

**Never:** the **Upgrade** button on the Billing page (the only way to get a bill).

---

## Step C1 part 2: who am I in AWS? (2026-10-24)

**Problem:** the plan said "turn on MFA for root, create a daily IAM user". The console
had no "Add MFA for root" button.

**What my screenshots showed:** I log in through a **project identity** ("Sign out of
Fresh Deploy"); IAM shows `AccountFullAccessRole` (used minutes ago), AWS-managed roles,
and "Root access management" offering only 2 actions (delete a bad S3 / SQS policy). So
root is **managed by AWS centrally**, and Organizations / Control Tower / Identity Center
are greyed out (I cannot turn them on even by mistake).

**Decision:** skip root MFA and the IAM user: there is no root password in use and no
access key. That is safer AND faster. (Budget alert: still to do.)

**Simple picture:** a serviced apartment. The building management (AWS) keeps the master
key; I get my own room key (the project login). I don't need to guard a master key I
never received.

---

## Step C3: Terraform files written and checked (2026-10-24) - not applied yet

| File | Creates |
|---|---|
| `infra/aws/versions.tf` | Terraform 1.16.5 + AWS provider 6.68.0 pinned; tags on everything |
| `variables.tf` | region Mumbai, t3.small, 20 GB, image `sha-2a64dc0`, domain, model, seed file |
| `security.tf` | the guard: in 80 + 443 only, no 22 |
| `iam.tf` | the server's badge: Session Manager + read `/docpilot/*` + read the seed bucket |
| `storage.tf` | private, versioned S3 bucket for the snapshot |
| `compute.tf` | t3.small Ubuntu 24.04, gp3 20 GB encrypted, CPU credits "standard", Elastic IP |
| `cloud-init.sh` | first boot: swap -> Docker -> AWS CLI -> files -> .env from SSM -> up -> seed |
| `outputs.tf` | public IP, instance id, bucket name |

**Checks:** `terraform fmt` + `validate` (Terraform 1.16.5 in Docker): "Success! The
configuration is valid." shellcheck: clean. Bundle for CloudShell:
`data/cloudshell/docpilot_infra.zip` + the snapshot (both gitignored).

**Small concepts:**
- `cpu_credits = "standard"`: t3 servers earn CPU "coins" when idle and spend them when
  busy. "unlimited" would BUY more coins (money); "standard" just slows down.
- **Why the server waits in loops:** the key and the snapshot are added by me AFTER the
  server exists (the bucket only exists after apply). The script politely retries every
  20 s instead of failing.

**Bug I caught:** `data/cloudshell/` was not gitignored; added before anything was pushed.

---

## Step C1-C3: AWS blocks Mumbai -> Sydney; plan read (2026-10-24)

**Problem 1: AccessDenied.** `ssm put-parameter` in Mumbai: "explicit deny in a service
control policy" (an **SCP**, AWS's rulebook for free-plan project accounts, set by AWS's
own management account; I cannot change it).

**How we found the cause (no guessing):** `aws iam simulate-principal-policy` (AWS's
"would this be allowed?" checker, creates nothing). IAM actions: allowed. EC2, S3, SSM,
Secrets Manager: denied. IAM is global, the others are regional -> a region rule. The
project page (Projects -> Fresh Deploy -> Additional info) says **Region: Asia Pacific
(Sydney) ap-southeast-2**. Storing the key in Sydney worked:
`/docpilot/GROQ_API_KEY  SecureString  1`.

**Fix:** `variables.tf` region -> `ap-southeast-2`. Honest cost: farther from India
(latency to be measured at launch) and t3.small Sydney about $0.0264 / h = about $19.3 /
month (holori.com, updated 2026-10-23) -> about $25 / month in total -> $100 lasts about
4 months; the credit activities stretch it.

**Problem 2: "no space left on device"** at `terraform init`: CloudShell home = 974 MB
and the AWS provider is several hundred MB. **Fix:** `export TF_DATA_DIR=/tmp/tfdata`
(plug-ins in `/tmp`: 10 GB free, wiped on restart -> just `terraform init` again); the
state stays in the home folder (kept).

**How I stored the key without it appearing on screen or in history:**
```bash
set +o history
aws ssm put-parameter --region ap-southeast-2 --name /docpilot/GROQ_API_KEY --type SecureString --query Version --value "<key>"
set -o history
aws ssm get-parameter --region ap-southeast-2 --name /docpilot/GROQ_API_KEY --query 'Parameter.[Name,Type,Version]' --output text
```

**The plan, read together:** `Plan: 13 to add, 0 to change, 0 to destroy.`
| Check | Plan says |
|---|---|
| everything | "will be created"; nothing destroyed or replaced |
| region | `ap-southeast-2` on every resource |
| server | `t3.small`, cpu_credits `standard`, IMDSv2 `required` |
| disk | 20 GB gp3, encrypted, deleted with the server |
| doors | in: 80 and 443 only (no 22); out: all |
| badge (role) | trusted only by `ec2.amazonaws.com`; reads `parameter/docpilot/*` + `GetObject` on the seed bucket; SSM core |
| bucket | `docpilot-seed-<account>`, public access blocked x4, versioning on |
| tags | `project=docpilot`, `managed_by=terraform` everywhere |
| image | `ubuntu-noble-24.04-amd64-server-20261023` |

**Important commands:**
```bash
export TF_DATA_DIR=/tmp/tfdata
terraform init
terraform plan -var domain=docpilot.duckdns.org -out tfplan
```

---

## Step C3: terraform apply, first try (2026-10-24) - 12 of 13 created

| Created | Time |
|---|---|
| S3 bucket + versioning + public access block, security group, egress + https rules, role + policy + SSM attachment, instance profile | 0-7 s each |
| `aws_instance.server` (`i-02226908d704d3c6b`) | 14 s |
| `aws_eip.server` | 2 s |
| `aws_vpc_security_group_ingress_rule.http` | **FAILED** |

**Error:** `InvalidParameterValue: Invalid rule description` -> the description "HTTP: Let's
Encrypt ..." has an apostrophe; AWS allows only `a-zA-Z0-9. _-:/()#,@[]+=&;{}!$*`.
`plan` cannot see this (AWS checks it only when creating), and the mentor missed it.
**Fix:** "Lets Encrypt". Re-plan must say `1 to add` (Terraform's state remembers the 12).

**Lesson:** `plan` checks the SHAPE of the request; the cloud's own rules are only checked
by the real API. A failed apply is not a disaster: state records what exists, so the next
apply continues from there (nothing is duplicated).

---

## Step C3-C6: apply finished, name pointed, LIVE (2026-10-24)

| Step | Result |
|---|---|
| re-plan after the fix | `Plan: 1 to add, 0 to change, 0 to destroy` (only the port-80 rule) |
| apply | `Apply complete! Resources: 1 added` -> all 13 exist |
| outputs | instance `i-02226908d704d3c6b`, public IP `13.238.193.153`, bucket `docpilot-seed-<account>`, Ubuntu `noble-24.04 ... 20261023` |
| snapshot upload | `aws s3 cp` to the seed bucket: OK |
| first look from my laptop | `http://13.238.193.153` -> **308** (Caddy's redirect to HTTPS): the stack was already running |
| DuckDNS | at first pointed to `223.185.48.133` (my HOME IP, DuckDNS's default) -> changed to `13.238.193.153` |
| `https://docpilot.duckdns.org/ready` | **`ready`**: models, qdrant, library, llm all true |
| `/api/library` | fastapi 68, pydantic 49, docker 56, cot 196, wikipedia 44 = 413 chunks (no interview notes) |
| certificate | issuer **Let's Encrypt (YE2)**, valid 2026-10-24 -> 2027-01-22 (Caddy renews it by itself) |
| headers | `Via: 1.1 Caddy`, `Server: uvicorn`, `Alt-Svc: h3` |
| `/health` from my laptop (India -> Sydney), n = 5, NEW connection each time | 1.23-1.41 s (includes DNS + TCP + TLS handshakes over a long distance; NOT the answer time) |

**Small concept: why DuckDNS showed my home IP.** When you create a name, DuckDNS fills in
the IP you are visiting FROM (your home router). A name must point at the SERVER.

**Important commands:**
```bash
terraform apply tfplan
terraform output
aws s3 cp ~/docpilot_public_2026-10-24.snapshot s3://docpilot-seed-431618680247/ --region ap-southeast-2
```
```powershell
nslookup docpilot.duckdns.org 1.1.1.1
curl.exe -s https://docpilot.duckdns.org/ready
```

**C5: first boot seen through Session Manager (2026-10-24):**
- Connect -> **SSM Session Manager** (NOT "EC2 Instance Connect", which wanted port 22 open:
  AWS's own yellow warning; we did not open it).
- `cloud-init-output.log` ends with: containers started -> snapshot downloaded from S3 ->
  `restored docpilot_v1_ft200: 413 chunks` -> `== DONE` -> "Cloud-init ... finished ...
  Up **319.10 seconds**": boot -> live in about **5.3 minutes**, no hands on the server.
- EC2 status: 3/3 checks passed.

**Real server numbers (t3.small Sydney, 2026-10-24, about 49 min after boot, n = 1):**
| Measure | Server | Laptop (B6) |
|---|---|---|
| containers | caddy Up, app Up **(healthy)**, qdrant Up | same |
| Caddy RAM | 18 MiB | 24 MiB |
| app RAM | **745 MiB** (after the first questions) | 516 idle / 681 after a question |
| Qdrant RAM | **28 MiB** | 448 MiB |
| whole server (`free -h`) | 1.9 GiB total, **1.1 GiB used, 806 MiB available**, swap 33 MiB of 2 GiB used | - |

**Why Qdrant shows 28 MiB here but 448 MiB on the laptop (honest):** Docker Desktop and
a real Linux server count memory differently (on Docker Desktop, file pages Qdrant reads
are counted as its memory; on the server most of that sits in the Linux page cache,
`buff/cache` 945 Mi). The comparable number is `available`: 806 MiB free with swap almost
untouched -> the 2 GB server is NOT tight right now. The heavy case (a 258-page upload,
app peak about 1.1 GB on the laptop) is still to be measured here.

**The learner's verdict:** "everything is working fine, we achieved it finally."

**README:** live demo link added.

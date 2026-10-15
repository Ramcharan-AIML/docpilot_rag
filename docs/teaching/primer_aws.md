# Primer: AWS From Zero (Part 1 of 2)

Used in: Phase 7 (account created at the **start of Phase 7**, decision D-017).
Part 1: what the cloud is, the free plan, account safety, and each service we use.
Part 2 (`2_primer_aws.md`): how DocPilot uses them together, cost traps, daily routine,
moving to Oracle.

Facts below marked "checked 2026-10-08" come from AWS pages on that date. Everything else
marked VERIFY is checked again on build day (Rule 4).

---

## 1. What "the cloud" is

**Like I'm five:** instead of buying a computer and keeping it in your room, you **rent** one
that lives in a huge building owned by Amazon. You control it over the internet. You can
rent a small one or a big one, for an hour or for a year, and give it back any time.

**Precisely:** AWS (Amazon Web Services) rents computing (servers), storage, databases,
networks, and hundreds of managed services, billed by usage.

| Word | Meaning |
|---|---|
| **Region** | A city-sized group of AWS data centres, e.g. `ap-south-1` (Mumbai). You pick one; resources live there |
| **Availability Zone (AZ)** | One or more separate buildings inside a region. Spreading across AZs survives a building failure |
| **Console** | The website where you click to manage AWS |
| **CLI** | The `aws` command-line tool: the same actions, typed |
| **Resource** | Anything you create: a server, a bucket, a network |

**Pick one region and stay in it.** Forgotten resources in another region are a classic cost
leak. Choose one near you (latency) that offers the free-plan instance types (VERIFY).

---

## 2. The AWS free plan (checked 2026-10-08)

| Fact | Value |
|---|---|
| Credits | USD 100 at sign-up, up to USD 100 more by trying foundational services |
| Duration | up to **6 months** or until credits are used, whichever comes first |
| Server time | paid **from the credits** (not free by itself) |
| Can you be charged beyond credits? | No, on the free plan you cannot exceed the limits |
| What happens at the end | account **suspended**; data kept 90 days; then **deleted** unless you upgrade to paid |
| Credit card | not required for most new customers (AWS may ask to verify identity) |
| Free-plan instance types | `t3.micro`, `t3.small`, `t4g.micro`, `t4g.small`, `c7i-flex.large`, `m7i-flex.large` |
| Restricted services | a subset of services is blocked on the free plan (those that would burn all credits at once); check each one before use |

**What this means for DocPilot (decisions D-017, D-018):**
1. We create the account at the **start of Phase 7**, so the 6 months cover deployment and your
   job-hunting demos.
2. Credits are a **budget**, not unlimited. We stop or shrink what we do not use.
3. Before month 6, we **move the deployment to Oracle Cloud Always Free** using the same
   Terraform and container setup. That move is itself a great interview story.

---

## 3. Account safety first (do these before creating anything)

**Like I'm five:** the **root user** is the master key to the whole house, including the
bank vault. You lock the master key in a safe and use a normal key every day.

1. **Root user:** use it once to set up, turn on **MFA** (a phone authenticator app), then
   stop using it.
2. **Daily user:** create an admin identity for yourself (IAM Identity Center or an IAM user,
   VERIFY the current recommended way), also with MFA. Use this every day.
3. **Cost alerts:** create an AWS Budget with email alerts (for example at 25%, 50%, 75% of
   your credits) and look at the Billing / Free Tier page weekly.
4. **No access keys on your laptop if you can avoid them:** prefer short-lived login
   (`aws sso login`, VERIFY) over permanent keys. Never put AWS keys in git, `.env.example`,
   or a Docker image.
5. **Tag everything** you create with `project=docpilot`, so you can find and delete it all.

---

## 4. IAM: who may do what

**Like I'm five:** IAM (Identity and Access Management) is the school's badge system. Each
badge says which doors it opens. A cleaner's badge opens the store room, not the head
teacher's office.

| IAM word | Meaning | DocPilot example |
|---|---|---|
| **User / identity** | a person who logs in | you |
| **Role** | a badge that a *machine or service* wears temporarily; no password | the EC2 server's role; the GitHub Actions role |
| **Policy** | the list of allowed actions on allowed resources (JSON) | "may pull images from ECR repo `docpilot`" |
| **Least privilege** | give only the doors that are needed | the server may read its own buckets, nothing else |
| **Instance profile** | how an EC2 server wears a role | lets boto3 on the server use S3 with **no keys** |
| **OIDC federation** | GitHub proves "I am the docpilot repo's workflow" and gets a short-lived role | CI pushes images to ECR with **no stored AWS keys** |

**Why roles instead of keys:** a key copied into a file can leak and works forever. A role
gives temporary credentials that expire on their own. Interviewers love this answer.

---

## 5. VPC: your private network

**Like I'm five:** a VPC (Virtual Private Cloud) is a fenced garden around your servers.
You decide where the gates are and who may walk through them.

| VPC word | Meaning | DocPilot choice |
|---|---|---|
| **VPC** | your private network with an address range (e.g. `10.0.0.0/16`) | one VPC for DocPilot |
| **Subnet** | a smaller section of the VPC, in one AZ | one **public** subnet (keeps it simple and cheap) |
| **Internet gateway** | the garden's door to the internet | attached, so the server can be reached |
| **Route table** | signposts: "internet traffic goes through the gateway" | one route `0.0.0.0/0 -> internet gateway` |
| **Security group** | a firewall on the server itself: which ports are open, to whom | 443 and 80 open to the world; **nothing else**; no SSH port (we use Session Manager) |
| **NAT gateway** | lets *private* subnets reach the internet | **not used**: it charges by the hour and per GB, a big credit drain for a small project |

**Why one public subnet and not the "textbook" private + public design?** The textbook design
needs a NAT gateway (expensive) or extra setup. For one small server, a tight security group
gives the protection we need. Interview answer: "I know the private-subnet pattern; for a
single-node portfolio deployment I chose a public subnet with a minimal security group and
no SSH, to avoid NAT costs. At larger scale I would move the app to private subnets behind a
load balancer."

---

## 6. EC2: the rented computer

**Like I'm five:** EC2 (Elastic Compute Cloud) gives you a computer you rent by the second.

| EC2 word | Meaning |
|---|---|
| **Instance** | one rented computer |
| **Instance type** | its size: CPU, RAM. E.g. `m7i-flex.large` (VERIFY: 2 vCPU, 8 GiB) |
| **AMI** | the starting disk image (e.g. Ubuntu) |
| **EBS volume** | the instance's hard disk (gp3 type). Persists if the instance stops |
| **User data / cloud-init** | a script that runs on first boot (installs Docker, etc.) |
| **Stop vs terminate** | stop = switch off (disk kept, still costs a little for storage); terminate = delete forever |
| **Elastic IP** | a fixed public address. Public IPv4 addresses cost USD 0.005 per hour each (checked 2026-10-08), paid from credits |
| **SSM Session Manager** | open a terminal on the server through AWS, with no SSH port open at all |

**Which size?** Our stack (API with embedding model and reranker, Qdrant, Redis, Postgres,
Prometheus, Grafana, Caddy, and later k3s) needs several GB of RAM. Among free-plan types,
`m7i-flex.large` has the most memory (VERIFY). We measure real RAM use with `docker stats`
first, then choose the smallest type that fits. Note: it is x86 (amd64); Oracle's free VM is
ARM (arm64), so we build images for **both** architectures.

---

## 7. S3: object storage in the cloud

The real version of what SeaweedFS does locally (see `primer_object_storage.md`). Same boto3
code; the endpoint setting is empty on AWS, and the server uses its IAM role instead of keys.
Buckets: raw docs, processed data, Qdrant snapshots, MLflow artifacts (optional), and the
Terraform state. All with **public access blocked**.

---

## 8. ECR: the image warehouse

**Like I'm five:** ECR (Elastic Container Registry) is a private warehouse for your Docker
images inside AWS. CI puts new images in; the server takes them out.

- CI (GitHub Actions) logs in with the OIDC role and pushes `docpilot-api:<git-sha>`.
- The EC2 server pulls with its instance role. No passwords anywhere.
- **Lifecycle policy:** keep only the last N images, so storage does not slowly eat credits.
- We also keep pushing to GitHub Container Registry (GHCR), which Oracle can pull from after
  the move.

---

## 9. CloudWatch: AWS's own monitoring

**Like I'm five:** CloudWatch is the building's security office: it watches every rented
room's electricity and temperature, collects the guards' notebooks, and rings an alarm when
something looks wrong.

| CloudWatch part | Use in DocPilot |
|---|---|
| **Metrics** | EC2 CPU, network, status checks (automatic); memory and disk via the CloudWatch agent |
| **Logs** | container logs shipped from the server (set a short **retention**, e.g. 7 days, so storage stays cheap) |
| **Alarms** | e.g. "status check failed" or "CPU above 90% for 10 minutes" -> email |
| **Dashboards** | optional; we use Grafana for app metrics |

**Why both CloudWatch and Prometheus/Grafana?** CloudWatch knows the **machine and AWS**
(is the server alive, disk full?). Prometheus knows **our app** (retrieval scores, refusal
rate, cache hits). Prometheus/Grafana also move to Oracle unchanged; CloudWatch is AWS-only.

Continued in [2_primer_aws.md](2_primer_aws.md)

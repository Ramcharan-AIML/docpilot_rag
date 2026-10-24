# Teach: AWS for our live link (Stage C)

Read this BEFORE you open the AWS sign-up page. Facts marked "checked 2026-10-24" come
from official AWS pages on that day; everything else is explained, not measured.

---

## 1. What AWS is (ELI5)

**Real-life example: renting a flat instead of building a house.** You do not buy land,
bricks or a generator. You rent a flat (a server), a storeroom (a disk), a letterbox with
a fixed address (an IP), and you pay per hour. When you leave, you hand back the keys and
the bill stops.

AWS = Amazon's shop of rented computers and services. We use only 6 things from it:

| AWS thing | Real-life picture | What it is for us |
|---|---|---|
| **EC2** instance | the rented flat | the Linux server that runs Caddy + app + Qdrant |
| **EBS** volume | the flat's built-in cupboard | the server's disk (20 GB): image, volumes, chats |
| **Elastic IP** | a fixed postal address | the public IP that never changes, so DuckDNS stays right |
| **Security group** | the building's guard with a list | lets in only ports 80 and 443 |
| **IAM** | keys and ID cards | who (you, the server) may do what |
| **SSM** | an intercom + a safe | Session Manager = a terminal in the browser; Parameter Store = the Groq key, encrypted |

Plus **S3** (a cloud folder: the seed snapshot), **CloudShell** (a terminal inside the
AWS website) and **Budgets** (an email when spending passes a line).

---

## 2. The free plan (checked 2026-10-24)

| Fact | Value | Source |
|---|---|---|
| Credits at sign-up | **$100** | [aws.amazon.com/free](https://aws.amazon.com/free/) |
| Extra credits from activities | up to **$100 more** (total $200) | same |
| How long | **6 months** from sign-up, or until credits run out, whichever is first | [EC2 free tier docs](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html) |
| Then | the account **closes by itself** (unless you upgrade to Paid). You are **not charged** on the Free plan | aws.amazon.com/free |
| Free-plan EC2 types (accounts from 2025-07-15) | t3.micro, **t3.small**, t4g.micro, t4g.small, c7i-flex.large, m7i-flex.large | EC2 free tier docs |
| India accounts (AISPL) | **not confirmed** on any official page: we check the Credits page right after sign-up | - |

**What this means for us (honest):**
- The free plan has a built-in seat belt: it cannot bill your card. The danger is not a
  bill; it is the **link dying** when credits end or month 6 arrives.
- So: the Oracle move (D-018) must happen **before month 6**, and budget alerts tell us how
  fast the credits go.

**The ONE way to get a bill:** clicking **"Upgrade to Paid plan"**. Never click it.

---

## 3. What it costs (from credits)

| Item | Price | Per month (730 h) | Source |
|---|---|---|---|
| EC2 t3.small, Mumbai | about $0.0224 / hour | about **$16.35** | third-party price list (holori.com); confirm in the EC2 console when launching |
| Public IPv4 (Elastic IP) | $0.005 / hour | **$3.65** | [aws.amazon.com/vpc/pricing](https://aws.amazon.com/vpc/pricing/) (checked) |
| EBS gp3 20 GB | about $0.08-0.09 / GB | about **$1.7** | not checked yet: confirm on the EBS price page |
| S3 (3 MB), SSM, Budgets | cents or free | about $0 | - |
| **Total** | | **about $22 / month** | |

$100 lasts about **4.5 months**; with $200 the 6-month limit comes first.

---

## 4. Accounts and keys (IAM): the most important safety lesson

| Who | Picture | Rule |
|---|---|---|
| **Root user** (your email) | the building's owner key: opens everything, even closing the account | MFA on, then put it in a drawer. Use only for billing and account settings |
| **IAM user** (e.g. `ram-admin`) | your daily house key | console login + MFA; **no access keys** |
| **IAM role** for the server | a staff badge the server wears | can read ONE secret path and ONE bucket, and talk to SSM. Nothing else |

**MFA** (multi-factor authentication) = password + a 6-digit code from an app on your
phone (Google Authenticator / Microsoft Authenticator). A stolen password alone is useless.

**Why no access keys?** An access key is a password written in a file. If it leaks (git,
a screenshot, a virus), anyone can start 100 servers on your account. We never create
one: Terraform runs in **CloudShell**, which uses your browser login.

**Role vs user (interview favourite):** a user is a person with a permanent password; a
role is a set of permissions that something *wears for a short time*. AWS gives the
server short-lived keys that rotate by themselves, so there is no key to steal.

---

## 5. Regions

A **region** = one AWS data-centre city. We use **Asia Pacific (Mumbai) `ap-south-1`**:
closest to you (fast for Indian visitors) and it has t3.small.

**Rule: one region only.** Resources in another region are invisible on the Mumbai pages,
so a forgotten one would quietly eat credits. Always check the top-right corner says
**Mumbai**.

---

## 6. The server's security: no door 22

| Port | Open? | Why |
|---|---|---|
| 443 (HTTPS) | yes, to everyone | the website |
| 80 (HTTP) | yes, to everyone | Let's Encrypt checks it, then Caddy redirects to 443 |
| 22 (SSH) | **no** | we use Session Manager instead |
| 8000, 6333 | **no** | only Caddy talks to the app; only the app talks to Qdrant |

**Session Manager:** the SSM agent on the server calls OUT to AWS and keeps a line open.
You click "Connect" in the console and get a terminal. Like an intercom: the visitor
cannot open the door from outside; the person inside picks up. No open port, no key
file, every session logged.

**Parameter Store (SecureString):** the Groq key is stored encrypted at
`/docpilot/GROQ_API_KEY`. On first boot the server (wearing its role) reads it and
writes `/opt/docpilot/.env` (root only). The key is never in git, never in the image,
never in Terraform files.

---

## 7. Terraform: the house plan on paper

**Real-life example: an architect's drawing.** Instead of telling the builder "a wall
here, a window there" by phone (clicking in the console), you hand over a drawing (`.tf`
files). The builder compares the drawing with the house and does only the difference.

| Word | Meaning |
|---|---|
| **provider** | the plug that lets Terraform talk to AWS (`hashicorp/aws`) |
| **resource** | one thing to create: an instance, a security group, a bucket |
| **state** | Terraform's notebook of what it already built (`terraform.tfstate`) |
| `terraform init` | download the provider |
| `terraform plan` | "here is what I WOULD change": read every line |
| `terraform apply` | do it (asks for `yes`) |
| `terraform destroy` | remove everything it built: the emergency brake |

**Why Terraform, not clicking?**
- Repeatable: the same files give the same server (the Oracle move reuses the idea).
- Reviewable: the plan shows every change before it happens.
- Removable: one `destroy` removes it all; no forgotten resources.

**Why not:** CloudFormation (AWS-only; Terraform also does Oracle later), CDK (needs a
programming setup), clicking (no record, easy to forget something that costs money).

**Versions we pin (checked 2026-10-24, each at least 2 weeks old):** Terraform **1.16.5**
(2026-10-02), AWS provider **6.68.0** (2026-10-07). Newer ones exist (1.17.0, 6.70.0) but
are only days old.

**State honesty:** for the deadline the state file lives in CloudShell's home folder (it
survives sessions, but CloudShell deletes it after about 120 days of no use: VERIFY).
We download a copy after every `apply`. An S3 state backend = Stage D.

---

## 8. Our exact setup

```text
CloudShell (browser, logged in as you)
   terraform apply  ──creates──►  security group (80, 443 in)
                                  IAM role + instance profile (SSM + read /docpilot/* + read bucket)
                                  S3 bucket (private, versioned) ◄── seed snapshot (uploaded once)
                                  EC2 t3.small, Ubuntu 24.04, gp3 20 GB, the role
                                  Elastic IP ──► DuckDNS name
First boot (cloud-init, runs once):
   install Docker → 2 GB swap → write compose + Caddyfile → read Groq key → .env
   → docker compose pull + up -d → seed the library from S3
```

**cloud-init** = a script AWS hands to the server on its very first boot (like the
welcome note for a new tenant: "install these, put this here"). It runs once.

**Swap** = a part of the disk used as slow extra RAM. B6 showed we peak near 2 GB; swap
means "slow for a moment" instead of "the app gets killed".

---

## 9. Money safety checklist (read before every session)

| Never | Why |
|---|---|
| "Upgrade to Paid plan" | only then can AWS charge the card |
| Organizations, Control Tower, IAM Identity Center | can switch the account to paid |
| NAT gateway, load balancer, EKS, anything not in this file | they burn credits fast |
| A second region | hidden resources |
| `yes` to a plan line you do not understand | ask first |
| Access keys | Section 4 |

Always: tags `project=docpilot`; budget alerts; Billing page once a week.

---

## 10. Interview questions

**Q: Why EC2 and not Lambda / App Runner / ECS?**
A: The app keeps 3 models (about 500 MB) in memory and streams answers. Lambda would
reload the models on cold starts. App Runner and ECS Fargate cost more and are not on
the free plan's short list. One small VM with Docker Compose is the simplest thing that
works, and B6 measured that it fits.

**Q: How does the server get the API key without it being in the image?**
A: An IAM role on the instance allows reading one SSM Parameter Store path. On first
boot, cloud-init reads the SecureString and writes a root-only `.env`. Nothing secret
lives in git, the image or Terraform.

**Q: How do you get into the server without SSH?**
A: SSM Session Manager. The agent connects outwards, so port 22 stays closed, there are
no key files, and sessions are logged.

**Q: How do you stop surprise bills?**
A: Free plan (cannot bill unless upgraded), one region, tags, budget alerts, everything
in Terraform so `destroy` removes it all, and a plan review before every apply.

**Q: What breaks first under load?**
A: RAM on the 2 GB server (B6: about 1.6 GB of containers at peak) and Groq's free
limits (A2). Both are protected: memory limits + swap, and rate limits + a queue of 2.

---

## 11. Real results (filled during Stage C)

| Check | Result | Date |
|---|---|---|
| Credits shown after sign-up (AISPL) | **$100.00**, Free plan, 183 days left (ends 2027-04-24) | 2026-10-24 |
| t3.small free-plan eligible in Mumbai (console) | n/a | |
| Live link up (HTTPS, Lets Encrypt, /ready ready) | https://docpilot.duckdns.org, Sydney t3.small | 2026-10-24 |
| Server RAM / start-up on t3.small | app 745 MiB, Qdrant 28 MiB, Caddy 18 MiB; 806 MiB available, swap 33 MiB; boot -> live 319 s | 2026-10-24 |
| First answer time from a phone | n/a | |

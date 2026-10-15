# Primer: Terraform (Infrastructure as Code)

Used in: Phase 7 (warm-up on your laptop first, then AWS, then Oracle). Decision: D-020.

---

## 1. Like I'm five

Building with LEGO, there are two ways:

1. **Clicking:** you build by hand from memory. Next time, you forget a piece. Nobody else
   can rebuild it exactly.
2. **The instruction booklet:** you write down every step. Anyone can build the exact same
   thing, again and again, and you can see exactly what changed between version 1 and 2.

**Terraform is the instruction booklet for cloud infrastructure.** You describe what should
exist (a network, a firewall, a server, a bucket) in text files. Terraform makes reality match
the files: it creates what is missing, changes what differs, deletes what you removed.
This is called **Infrastructure as Code (IaC)**.

---

## 2. The words

| Word | Meaning | Example |
|---|---|---|
| **Provider** | a plugin that knows how to talk to one platform | `aws`, `oci` (Oracle), `docker` |
| **Resource** | one thing to create | `aws_instance.app`, `aws_s3_bucket.snapshots` |
| **Data source** | something to **read**, not create | "latest Ubuntu AMI id" |
| **Variable** | an input value | `instance_type`, `region` |
| **Output** | a value printed after apply | the server's public IP |
| **Module** | a reusable folder of resources | `modules/aws_app_host` |
| **State** | Terraform's memory: a file listing what it created and their real ids | `terraform.tfstate` |
| **Backend** | where the state file is stored | local file (warm-up), S3 bucket (AWS) |
| **Plan** | a dry run: "here is what I *would* change" | `terraform plan` |
| **Apply** | do it | `terraform apply` |
| **Destroy** | delete everything this configuration created | `terraform destroy` |

**The language** is HCL (HashiCorp Configuration Language): blocks of `name = value`.

---

## 3. The workflow (always the same)

```powershell
terraform init       # download providers, connect the backend (once per folder)
terraform fmt        # tidy formatting
terraform validate   # syntax and reference check
terraform plan       # READ THIS CAREFULLY: + create, ~ change, - destroy
terraform apply      # type "yes" only if the plan is what you expected
terraform output     # show outputs (e.g. the IP)
terraform destroy    # remove everything (when done, or for the EKS exercise)
```

**Golden rule:** never `apply` a plan you did not read. A `-` (destroy) line on your database
is how people lose data.

---

## 4. What our code looks like (sketch)

```hcl
# infra/modules/aws_app_host/main.tf   (VERIFY all arguments against current provider docs)

resource "aws_security_group" "app" {
  name   = "docpilot-app"
  vpc_id = var.vpc_id

  ingress {                       # HTTPS from anywhere
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {                       # HTTP only for the certificate challenge / redirect
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {                        # the server may call out (LLM APIs, ECR, S3)
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  # No port 22: we use SSM Session Manager instead of SSH.
  tags = { project = "docpilot" }
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type            # e.g. "m7i-flex.large"
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.app.id]  # reference: Terraform orders the work
  iam_instance_profile   = aws_iam_instance_profile.app.name
  user_data              = file("${path.module}/../../bootstrap/cloud-init.sh")
  root_block_device {
    volume_size = var.disk_gb
    volume_type = "gp3"
  }
  tags = { project = "docpilot", Name = "docpilot-app" }
}

output "public_ip" {
  value = aws_instance.app.public_ip
}
```

Notice `aws_security_group.app.id` inside the instance: Terraform sees the reference and
creates the security group **first**. You describe *what*, Terraform works out the *order*.

---

## 5. State: Terraform's memory (and why it matters)

**Like I'm five:** state is Terraform's notebook of "things I built and their serial numbers".
Lose the notebook, and Terraform no longer knows it built anything; it would try to build
everything again.

| Rule | Why |
|---|---|
| Never commit `terraform.tfstate` to git | it can contain secrets and it changes constantly (gitignored) |
| On AWS, store it in an **S3 bucket** with versioning | shared, durable, and you can roll back a bad state |
| Use **state locking** | two applies at once would corrupt it. Recent Terraform can lock with a file in the S3 bucket itself (VERIFY current option, e.g. `use_lockfile`) |
| Never edit state by hand | use `terraform state` commands if ever needed |

**Chicken and egg:** the state bucket must exist before Terraform can use it. We create it
once with a tiny separate config (`infra/bootstrap_state/`) that keeps its own state locally.

---

## 6. Portable between AWS and Oracle (honestly)

Terraform does **not** magically turn AWS code into Oracle code. Resources are
provider-specific (`aws_instance` vs `oci_core_instance`). Portability comes from **structure**:

```text
infra/
├── bootstrap/cloud-init.sh        # SHARED: install Docker/k3s, pull images, start the app
├── bootstrap_state/               # one-time: create the S3 state bucket (AWS)
├── modules/
│   ├── aws_app_host/              # VPC, subnet, SG, IAM role, EC2, S3, ECR, CloudWatch
│   └── oracle_app_host/           # VCN, subnet, security list, A1 VM, bucket
├── envs/
│   ├── aws/        main.tf  variables.tf  terraform.tfvars.example   (uses aws_app_host)
│   └── oracle/     main.tf  variables.tf  terraform.tfvars.example   (uses oracle_app_host)
└── eks_exercise/                  # separate! plan-only by default; never left running
```

Both modules expose the **same outputs** (`public_ip`, `bucket_name`) and run the **same
boot script**. Everything above the machine (containers, manifests, app) is identical.

---

## 7. Terraform licence note (checked 2026-10-08)

Terraform changed in 2023 from an open-source licence to the Business Source License (BSL).
Using it to manage **your own** infrastructure is free. **OpenTofu** is a community fork under
the Linux Foundation, open source (MPL 2.0), and runs the same HCL for almost all workflows.
We write plain HCL that works in both and record the exact version used. If an interviewer
asks: "I used Terraform; I know OpenTofu exists because of the BSL change and my code runs on
either."

---

## 8. Why Terraform (and why not the alternatives)

| Option | Why not (for us) |
|---|---|
| Clicking in the console | not repeatable, not reviewable, easy to forget a resource (and pay for it) |
| AWS CloudFormation / CDK | AWS-only; we need the same tool for Oracle |
| Pulumi | real programming languages, good tool; Terraform/HCL is far more common in job descriptions |
| Shell scripts with the AWS CLI | no state, no plan; deleting things cleanly is hard |

---

## 9. Learning order in Phase 7

1. **Warm-up on your laptop (no cloud, no cost):** the Docker provider (VERIFY) creates a
   Qdrant container from Terraform. Learn init / plan / apply / destroy and state safely.
2. **AWS:** state bucket, then the full `envs/aws`. Read every plan line.
3. **EKS exercise:** `terraform plan` only by default.
4. **Oracle:** `envs/oracle` before month 6 of the free plan.

---

## 10. Self-check

1. Explain IaC with the LEGO-booklet story.
2. Provider vs resource vs module vs state?
3. What does `plan` show, and why must you read it?
4. Why is state stored in S3 with versioning and locking, and never in git?
5. How do we make the setup portable between AWS and Oracle, honestly?
6. Terraform vs OpenTofu: what is the licence story?

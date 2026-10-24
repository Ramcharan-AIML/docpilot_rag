# DocPilot live link on AWS (Phase 7 Stage C, D-069).
# Teaching: docs/production/06_teach_aws_live.md
# Runs in AWS CloudShell (your browser login): no access keys anywhere.

terraform {
  # Exact versions (checked 2026-10-24; each at least 2 weeks old): same result every time.
  required_version = "= 1.16.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.68.0"
    }
  }
  # State = Terraform's notebook of what it built. For the deadline it is a local file in
  # CloudShell's home folder (download a copy after every apply). S3 backend = Stage D.
}

provider "aws" {
  region = var.region

  # Every resource gets these tags: "what is this and who made it?" is always answerable,
  # and the Billing page can filter by project.
  default_tags {
    tags = {
      project    = "docpilot"
      managed_by = "terraform"
    }
  }
}

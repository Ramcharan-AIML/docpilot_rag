# Everything that could change lives here, nothing is hard-coded in the other files.

variable "region" {
  description = "The ONE region we use (money rule: one region only)."
  type        = string
  # Sydney, not Mumbai: the free-plan project "Fresh Deploy" is tied to ap-southeast-2 and
  # AWS's rulebook (an SCP) denies EC2 / S3 / SSM in other regions (C1, 2026-10-24).
  default = "ap-southeast-2"
}

variable "instance_type" {
  description = "Free-plan eligible; B6 measured about 1.6 GB of containers at peak."
  type        = string
  default     = "t3.small" # 2 vCPU, 2 GB RAM
}

variable "disk_gb" {
  description = "Root disk: Ubuntu + Docker + the 1.86 GB image + volumes + 2 GB swap."
  type        = number
  default     = 20
}

variable "app_image" {
  description = "Exact image the server runs: a sha tag, never latest (rollback = old tag)."
  type        = string
  default     = "ghcr.io/ramcharan-aiml/docpilot:sha-2a64dc0"
}

variable "domain" {
  description = "The DuckDNS name, e.g. docpilot.duckdns.org (Caddy gets the certificate)."
  type        = string
}

variable "llm_model" {
  description = "Groq model name (not secret). The key itself is in SSM Parameter Store."
  type        = string
  default     = "openai/gpt-oss-120b"
}

variable "seed_file" {
  description = "Name of the public library snapshot uploaded to the seed bucket."
  type        = string
  default     = "docpilot_public_2026-10-24.snapshot"
}

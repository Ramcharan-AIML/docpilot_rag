# The server (EC2), its disk (EBS) and its fixed address (Elastic IP).

# Newest Ubuntu 24.04 LTS from Canonical (owner id 099720109477 = Canonical's account).
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
}

resource "aws_instance" "server" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  vpc_security_group_ids = [aws_security_group.web.id]
  iam_instance_profile   = aws_iam_instance_profile.server.name

  # "standard" = when the CPU credits run out the server slows down; it never buys extra
  # CPU time ("unlimited" can cost money beyond the hourly price).
  credit_specification {
    cpu_credits = "standard"
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.disk_gb
    encrypted             = true
    delete_on_termination = true
  }

  # IMDSv2 only (the safer version of the server's "who am I" service).
  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  # First-boot script. The two files are passed as base64 so their own ${...} text is
  # not touched by Terraform.
  # replace(): drop Windows line endings (\r) in case git checked the file out with them.
  user_data = replace(templatefile("${path.module}/cloud-init.sh", {
    region       = var.region
    app_image    = var.app_image
    domain       = var.domain
    llm_model    = var.llm_model
    seed_bucket  = aws_s3_bucket.seed.id
    seed_file    = var.seed_file
    compose_b64  = filebase64("${path.module}/../../docker-compose.prod.yml")
    caddyfile_64 = filebase64("${path.module}/../../deploy/Caddyfile")
  }), "\r", "")

  tags = {
    Name = "docpilot-server"
  }

  lifecycle {
    # A newer Ubuntu image or an edited script must NOT silently replace the running
    # server (and its data). Updates go through Session Manager (C9).
    ignore_changes = [ami, user_data]
  }
}

# A fixed public IP: DuckDNS points at it and it survives stop / start.
resource "aws_eip" "server" {
  domain   = "vpc"
  instance = aws_instance.server.id
  tags = {
    Name = "docpilot-ip"
  }
}

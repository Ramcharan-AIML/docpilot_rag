# The server's staff badge (an IAM role). Least privilege: it can talk to Session Manager,
# read the /docpilot/* parameters, and read the seed bucket. Nothing else.

data "aws_caller_identity" "me" {}

# "Who may wear this badge?" Only EC2 instances.
data "aws_iam_policy_document" "ec2_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "server" {
  name               = "docpilot-server"
  assume_role_policy = data.aws_iam_policy_document.ec2_trust.json
}

# AWS's own policy for Session Manager (the browser terminal; no SSH, no port 22).
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.server.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "app_reads" {
  # The Groq key (SecureString). Only our path, nothing else in Parameter Store.
  statement {
    actions   = ["ssm:GetParameter"]
    resources = ["arn:aws:ssm:${var.region}:${data.aws_caller_identity.me.account_id}:parameter/docpilot/*"]
  }
  # The seed snapshot. Read only, only this bucket.
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.seed.arn}/*"]
  }
}

resource "aws_iam_role_policy" "app_reads" {
  name   = "docpilot-app-reads"
  role   = aws_iam_role.server.id
  policy = data.aws_iam_policy_document.app_reads.json
}

# An instance profile = the clip that attaches the badge (role) to the server.
resource "aws_iam_instance_profile" "server" {
  name = "docpilot-server"
  role = aws_iam_role.server.name
}

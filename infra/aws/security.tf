# The building's guard: only web traffic gets in. No port 22 (we use Session Manager),
# no 8000 / 6333 (only Caddy talks to the app, only the app talks to Qdrant).

# The default VPC exists in every account and is free. A custom VPC = Stage D.
data "aws_vpc" "default" {
  default = true
}

resource "aws_security_group" "web" {
  name        = "docpilot-web"
  description = "DocPilot: HTTP and HTTPS in, everything out"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_vpc_security_group_ingress_rule" "http" {
  security_group_id = aws_security_group.web.id
  # No apostrophe: AWS allows only a-zA-Z0-9. _-:/()#,@[]+=&;{}!$* here (C3, 2026-10-24).
  description = "HTTP: Lets Encrypt check + redirect to HTTPS"
  cidr_ipv4   = "0.0.0.0/0"
  ip_protocol = "tcp"
  from_port   = 80
  to_port     = 80
}

resource "aws_vpc_security_group_ingress_rule" "https" {
  security_group_id = aws_security_group.web.id
  description       = "HTTPS: the website"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

# Out: the server must reach GHCR (image), Groq (answers), Let's Encrypt, apt, and AWS
# (SSM, S3). "-1" = all protocols.
resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.web.id
  description       = "All outbound"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

# Printed after "terraform apply": copy them into the next steps.

output "public_ip" {
  description = "Put this IP into DuckDNS."
  value       = aws_eip.server.public_ip
}

output "instance_id" {
  description = "EC2 -> this instance -> Connect -> Session Manager."
  value       = aws_instance.server.id
}

output "seed_bucket" {
  description = "Upload the snapshot here (aws s3 cp)."
  value       = aws_s3_bucket.seed.id
}

output "ami_name" {
  description = "Which Ubuntu image the server started from."
  value       = data.aws_ami.ubuntu.name
}

# A private S3 bucket for the seed snapshot (the packed library box, 3.1 MB).
# Bucket names are global across all of AWS, so the account id makes ours unique.

resource "aws_s3_bucket" "seed" {
  bucket = "docpilot-seed-${data.aws_caller_identity.me.account_id}"
  # Only a re-creatable snapshot lives here, so "terraform destroy" may empty it.
  force_destroy = true
}

# Nobody on the internet can read it, even by mistake.
resource "aws_s3_bucket_public_access_block" "seed" {
  bucket                  = aws_s3_bucket.seed.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Versioning: uploading a new snapshot keeps the old one (undo button).
resource "aws_s3_bucket_versioning" "seed" {
  bucket = aws_s3_bucket.seed.id
  versioning_configuration {
    status = "Enabled"
  }
}

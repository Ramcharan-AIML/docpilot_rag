"""Object storage with the S3 API: SeaweedFS on the laptop, Amazon S3 on AWS (step 3.1b).

The same functions work on both. Only config.S3_ENDPOINT_URL changes: set = SeaweedFS (or any
S3-compatible store), empty = real AWS S3. On AWS the keys are empty too, and boto3 finds
the machine's IAM role by itself. Like qdrant_store.py, this is the only file that talks
to the object store.
"""

from pathlib import Path

import boto3

from docpilot import config


def get_s3_client(endpoint_url: str | None = None):
    """An S3 client. `endpoint_url` overrides the configured one (snapshots use the
    address Docker containers see); "" or no endpoint at all = real AWS S3."""
    endpoint = config.S3_ENDPOINT_URL if endpoint_url is None else endpoint_url
    options: dict = {"region_name": config.AWS_REGION}
    if endpoint:
        options["endpoint_url"] = endpoint
    if config.S3_ACCESS_KEY:  # laptop only; on AWS boto3 uses the IAM role instead
        options["aws_access_key_id"] = config.S3_ACCESS_KEY
        options["aws_secret_access_key"] = config.S3_SECRET_KEY
    return boto3.client("s3", **options)


def ensure_bucket(client, bucket: str) -> bool:
    """Create the bucket if it is missing. Returns True if it was created now."""
    existing = {item["Name"] for item in client.list_buckets().get("Buckets", [])}
    if bucket in existing:
        return False
    if config.AWS_REGION == "us-east-1":  # S3 rule: us-east-1 must NOT name a location
        client.create_bucket(Bucket=bucket)
    else:
        location = {"LocationConstraint": config.AWS_REGION}
        client.create_bucket(Bucket=bucket, CreateBucketConfiguration=location)
    return True


def upload_file(client, local_path: Path, bucket: str, key: str) -> None:
    client.upload_file(str(local_path), bucket, key)  # big files go up in parts automatically


def download_file(client, bucket: str, key: str, local_path: Path) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    client.download_file(bucket, key, str(local_path))


def list_keys(client, bucket: str, prefix: str = "", page_size: int = 1000) -> list[str]:
    """Every key under `prefix`, sorted.

    S3 returns at most 1000 keys per request; the paginator keeps asking until all are
    listed. Without it, a big bucket silently looks like it has 1000 files.
    """
    paginator = client.get_paginator("list_objects_v2")
    pages = paginator.paginate(
        Bucket=bucket, Prefix=prefix, PaginationConfig={"PageSize": page_size}
    )
    return sorted(item["Key"] for page in pages for item in page.get("Contents", []))


def upload_folder(client, folder: Path, bucket: str, prefix: str) -> int:
    """Upload every file under `folder` as `<prefix><relative path>`. Returns the count."""
    count = 0
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        # as_posix(): S3 keys use "/" on every system, also when uploaded from Windows
        upload_file(client, path, bucket, prefix + path.relative_to(folder).as_posix())
        count += 1
    return count


def download_prefix(client, bucket: str, prefix: str, folder: Path) -> int:
    """Download every key under `prefix` into `folder`, rebuilding the subfolders."""
    keys = list_keys(client, bucket, prefix)
    for key in keys:
        download_file(client, bucket, key, folder / key[len(prefix) :])
    return len(keys)


def presigned_get_url(client, bucket: str, key: str, seconds: int = 3600) -> str:
    """A temporary download link that works without keys (used to restore snapshots).

    The link is signed for the client's endpoint, so make the client with the address
    of whoever will open the link.
    """
    return client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=seconds
    )

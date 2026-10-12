# Primer: Object Storage (S3, SeaweedFS, boto3)

Used from: Phase 3 step 3.1b (local SeaweedFS), Phase 7 (real Amazon S3). Decision: D-019.

**Name change:** you asked for MinIO. On 2026-10-08 we checked: MinIO's free community
edition was archived (April 2026) and its Docker images and binaries were removed
(September 2026). Running a frozen, unpatched copy is a security risk. We use **SeaweedFS**
instead: same idea, free (Apache-2.0), still maintained. Your code does not change, because
it talks the S3 language, not "MinIO" or "SeaweedFS".

---

## 1. Like I'm five

Think of a giant **coat-check room** at a theatre.

- You hand over a coat (a **file**), and get a **ticket** with a name on it (the **key**),
  e.g. `docs/fastapi/query-params.md`.
- The coats hang in different **rooms** (**buckets**), e.g. `docpilot-raw-docs`.
- You do not care which hook or shelf it is on. Give the ticket, get the coat back.
- There are no real folders, just long ticket names with slashes that *look* like folders.

That is **object storage**. Amazon's version is **S3** (Simple Storage Service). Many other
products speak exactly the same "coat-check language" (the **S3 API**), so a program written
for one works with all of them.

---

## 2. Why not just use normal folders on disk?

| Normal disk folder | Object storage |
|---|---|
| Lives on one machine; dies with it | Separate service; survives servers being replaced |
| Hard to share between containers / servers | Any program with permission can read it over the network |
| Size limited to the disk | Grows as needed |
| No built-in versioning | Can keep old versions of each file |

In production, servers are **replaceable** (cattle, not pets). Anything that must survive goes
into a database or object storage, never only on the server's disk.

---

## 3. What DocPilot stores there

| Bucket | Contents | Why |
|---|---|---|
| `docpilot-raw-docs` | downloaded documentation files | ingestion on any machine reads the same input |
| `docpilot-processed` | cleaned docs, contextual-chunk cache, extracted tables | expensive to rebuild (LLM calls) |
| `docpilot-snapshots` | Qdrant snapshots (backup of the vector DB) | restore or move the index without re-embedding |
| `docpilot-mlflow` | MLflow artifacts (results JSON, CSVs) | MLflow server stores its "stapled files" here |
| `docpilot-tfstate` (AWS only, Phase 7) | Terraform state file | shared, versioned record of what infrastructure exists |

The `data/docs/` folder stays gitignored; object storage is where those files live outside
your laptop.

---

## 4. boto3: the Python remote control for S3

`boto3` is AWS's official Python library. It speaks the S3 API, so it can talk to SeaweedFS
on your laptop **or** real S3, depending on one setting: the **endpoint URL**.

```python
# src/docpilot/storage/object_store.py (sketch; VERIFY boto3 API on build day)
import boto3

from docpilot import config


def get_s3_client():
    """Same code for SeaweedFS (local) and Amazon S3 (cloud).

    Local:  S3_ENDPOINT_URL=http://localhost:8333  (SeaweedFS's S3 port, VERIFY)
    AWS:    S3_ENDPOINT_URL is empty -> boto3 uses real S3, and credentials come from the
            server's IAM role (no keys in files at all).
    """
    return boto3.client(
        "s3",
        endpoint_url=config.S3_ENDPOINT_URL or None,   # None = real AWS S3
        region_name=config.AWS_REGION,
    )


def upload_file(local_path: str, bucket: str, key: str) -> None:
    get_s3_client().upload_file(local_path, bucket, key)


def download_file(bucket: str, key: str, local_path: str) -> None:
    get_s3_client().download_file(bucket, key, local_path)


def list_keys(bucket: str, prefix: str = "") -> list[str]:
    """All keys under a 'folder-looking' prefix, e.g. 'fastapi/'."""
    paginator = get_s3_client().get_paginator("list_objects_v2")
    keys: list[str] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            keys.append(item["Key"])
    return keys
```

**The big idea: "switch to real S3 by changing the endpoint".** On your laptop
`S3_ENDPOINT_URL` points at SeaweedFS. On AWS it is empty, and the same functions use S3.
That is the swappable-provider principle (guiding principle 3) applied to storage.

**Why a paginator:** S3 returns at most about 1000 keys per request. A paginator asks again
until everything is listed. Forgetting it is a classic bug that only appears with big buckets.

---

## 5. SeaweedFS in Docker (Phase 3)

```yaml
# docker-compose.yml (sketch; VERIFY image name, tag, ports, and flags in SeaweedFS docs)
services:
  seaweedfs:
    image: chrislusf/seaweedfs:<pinned-tag>
    command: "server -s3 -dir=/data"     # one container: storage + S3 gateway
    ports:
      - "8333:8333"                       # S3 API
    volumes:
      - ./seaweed_data:/data              # gitignored
```

Local access keys for SeaweedFS go in `.env` (never in git), configured as SeaweedFS's docs
describe. On AWS we use no keys at all (IAM roles, see `primer_aws.md`).

**Why SeaweedFS over the alternatives (decision D-019):** RustFS is very MinIO-like but much
younger; Garage is tiny but AGPL and needs a cluster layout step; LocalStack emulates many AWS
services but is heavier than we need. SeaweedFS is mature, Apache-2.0, one container.

---

## 6. Safety rules for buckets

1. **Block public access** on every bucket (the AWS default for new buckets; keep it on).
   Many real data leaks were public S3 buckets.
2. Least privilege: the app may read/write only its own buckets.
3. Versioning on the Terraform state bucket (undo a bad change).
4. Lifecycle rules to delete old snapshots automatically (storage costs credits on AWS).
5. Never put API keys in object storage.

---

## 7. Self-check

1. Explain bucket, key, and object with the coat-check story.
2. Why do production servers keep important files in object storage, not on their disk?
3. How does the same boto3 code talk to SeaweedFS and to S3?
4. Why did we not use MinIO?
5. What is a paginator for?
6. Name three bucket safety rules.

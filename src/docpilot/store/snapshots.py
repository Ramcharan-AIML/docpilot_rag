"""Back up a Qdrant collection to object storage and restore it (step 3.1b).

A snapshot is one file holding a whole collection: vectors, payloads and settings. Phase 7
uses it to move the index between clouds WITHOUT re-embedding (453 chunks take ~45 s on
this laptop; a big corpus would take hours).

Backup:  Qdrant writes a snapshot -> we download it -> upload to the snapshot bucket.
Restore: we make a temporary download link (presigned URL) -> Qdrant fetches the file
         itself and rebuilds the collection. The file never passes through Python twice.
Needs Qdrant as a server (config.QDRANT_URL): local mode has no snapshot files.
"""

import shutil
import tempfile
import urllib.request
from pathlib import Path

from qdrant_client import QdrantClient

from docpilot import config
from docpilot.storage.object_store import (
    get_s3_client,
    list_keys,
    presigned_get_url,
    upload_file,
)


def snapshot_key(collection: str, snapshot_name: str) -> str:
    """Keys are grouped per collection: 'docpilot_v1_ft200/<snapshot file name>'."""
    return f"{collection}/{snapshot_name}"


def backup_collection(qdrant: QdrantClient, s3, collection: str) -> str:
    """Snapshot `collection`, store it in the snapshot bucket, return its key."""
    if not config.QDRANT_URL:
        raise RuntimeError("snapshots need Qdrant as a server: set QDRANT_URL (step 3.1)")
    description = qdrant.create_snapshot(collection, wait=True)
    if description is None:
        raise RuntimeError(f"Qdrant made no snapshot of {collection!r}")
    url = f"{config.QDRANT_URL}/collections/{collection}/snapshots/{description.name}"
    key = snapshot_key(collection, description.name)
    with tempfile.TemporaryDirectory() as folder:
        local = Path(folder) / description.name
        with urllib.request.urlopen(url) as response, local.open("wb") as out:
            shutil.copyfileobj(response, out)  # streamed: the file is never all in memory
        upload_file(s3, local, config.SNAPSHOT_BUCKET, key)
    # The copy in the bucket is the backup; keep the Qdrant server's disk clean.
    qdrant.delete_snapshot(collection, description.name, wait=True)
    return key


def latest_snapshot_key(s3, collection: str) -> str | None:
    """Newest backup of `collection` (snapshot names end with a date and time)."""
    keys = list_keys(s3, config.SNAPSHOT_BUCKET, f"{collection}/")
    return keys[-1] if keys else None


def restore_collection(qdrant: QdrantClient, key: str, target: str) -> None:
    """Rebuild collection `target` from the snapshot at `key` (replaces it if it exists)."""
    if not config.QDRANT_URL:
        raise RuntimeError("snapshots need Qdrant as a server: set QDRANT_URL (step 3.1)")
    # The link must work for QDRANT (inside Docker), so it is signed for the address Qdrant
    # sees: http://seaweedfs:8333 on the laptop, real S3 on AWS.
    s3_seen_by_qdrant = get_s3_client(config.S3_ENDPOINT_URL_DOCKER or None)
    link = presigned_get_url(s3_seen_by_qdrant, config.SNAPSHOT_BUCKET, key, seconds=600)
    qdrant.recover_snapshot(target, location=link, wait=True)

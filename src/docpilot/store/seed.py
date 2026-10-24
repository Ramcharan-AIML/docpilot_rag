"""Fill an EMPTY Qdrant with the main library from a snapshot file (Phase 7 B4, D-066).

Real-life example: moving house with packed boxes. The library was built (cleaned,
chunked, embedded) once on the laptop; the server just unpacks the box. No Docling, no
re-embedding, the same vectors, so the same retrieval scores as measured.

Safe to run again: if the library is already there, it does nothing (use --force to
replace it, e.g. with a newer snapshot).

On the laptop's prod stack (B4) and on the server (C4), inside the app container:
  docker compose -f docker-compose.prod.yml run --rm -v ./data/snapshots:/seed:ro app \
      python -m docpilot.store.seed /seed/docpilot_public_<date>.snapshot
"""

import argparse
from pathlib import Path

from qdrant_client import QdrantClient, models

from docpilot import config
from docpilot.store.qdrant_store import get_client


def has_library(qdrant: QdrantClient, collection: str = config.COLLECTION_NAME) -> bool:
    return qdrant.collection_exists(collection) and qdrant.count(collection).count > 0


def upload_snapshot(qdrant: QdrantClient, path: Path, collection: str, checksum: str | None):
    """Send the file to Qdrant, which rebuilds the collection from it.

    priority=snapshot: the file's data wins (Qdrant's docs: for moving data between
    clusters). checksum: Qdrant compares it with the file and refuses a damaged copy.
    """
    with path.open("rb") as file:
        qdrant.http.snapshots_api.recover_from_uploaded_snapshot(
            collection_name=collection,
            wait=True,
            priority=models.SnapshotPriority.SNAPSHOT,
            checksum=checksum,
            snapshot=file,
        )


def seed(qdrant: QdrantClient, path: Path, force: bool = False) -> str:
    """'skipped' if the library is already there, else restore it; returns what happened."""
    if has_library(qdrant) and not force:
        return "skipped: the library is already there"
    checksum_file = path.with_suffix(".sha256")
    checksum = checksum_file.read_text(encoding="utf-8").strip() if checksum_file.exists() else None
    upload_snapshot(qdrant, path, config.COLLECTION_NAME, checksum)
    count = qdrant.count(config.COLLECTION_NAME, exact=True).count
    return f"restored {config.COLLECTION_NAME}: {count} chunks"


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore the main library from a snapshot.")
    parser.add_argument(
        "snapshot", type=Path, help="the .snapshot file (from make_public_snapshot)"
    )
    parser.add_argument("--force", action="store_true", help="replace an existing library")
    args = parser.parse_args()
    qdrant = get_client()
    try:
        print(seed(qdrant, args.snapshot, args.force))
    finally:
        qdrant.close()


if __name__ == "__main__":
    main()

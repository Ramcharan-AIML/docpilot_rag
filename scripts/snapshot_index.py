"""Back up a Qdrant collection to the snapshot bucket, or restore it (step 3.1b).

Run: python scripts/snapshot_index.py --backup                    (the app's collection)
     python scripts/snapshot_index.py --list
     python scripts/snapshot_index.py --restore --target docpilot_v1_ft200_restored
         (newest backup of the app's collection; --key <key> picks another one)

Needs Qdrant in Docker (QDRANT_URL) and SeaweedFS (S3_ENDPOINT_URL), or AWS in Phase 7.
"""

import argparse
import sys

from docpilot import config
from docpilot.storage.object_store import get_s3_client, list_keys
from docpilot.store.qdrant_store import get_client
from docpilot.store.snapshots import backup_collection, latest_snapshot_key, restore_collection


def main() -> None:
    parser = argparse.ArgumentParser(description="Qdrant snapshots <-> object storage.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--backup", action="store_true")
    action.add_argument("--restore", action="store_true")
    action.add_argument("--list", action="store_true")
    parser.add_argument("--collection", default=config.COLLECTION_NAME)
    parser.add_argument("--key", help="--restore: this backup instead of the newest")
    parser.add_argument("--target", help="--restore: collection to create (default: same)")
    args = parser.parse_args()

    s3 = get_s3_client()
    if args.list:
        for key in list_keys(s3, config.SNAPSHOT_BUCKET, f"{args.collection}/"):
            print(key)
        return

    qdrant = get_client()
    try:
        if args.backup:
            key = backup_collection(qdrant, s3, args.collection)
            print(f"{args.collection} -> s3://{config.SNAPSHOT_BUCKET}/{key}")
            return
        key = args.key or latest_snapshot_key(s3, args.collection)
        if key is None:
            sys.exit(f"no backup of {args.collection} in {config.SNAPSHOT_BUCKET}")
        target = args.target or args.collection
        restore_collection(qdrant, key, target)
        count = qdrant.count(target, exact=True).count
        print(f"s3://{config.SNAPSHOT_BUCKET}/{key} -> collection {target}: {count} points")
    finally:
        qdrant.close()


if __name__ == "__main__":
    main()

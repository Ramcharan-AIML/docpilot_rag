"""Copy the corpus to object storage, or restore it on a fresh machine (step 3.1b).

Run: python scripts/04_sync_docs.py --create-buckets   (once: raw docs, snapshots, MLflow)
     python scripts/04_sync_docs.py                    (upload data/docs + data/code)
     python scripts/04_sync_docs.py --download         (fresh clone: restore both folders)
     python scripts/04_sync_docs.py --download --to D:/tmp/corpus   (restore elsewhere)

Why: the corpus is not in git (licences, D-030). With a copy in the bucket, a new laptop or
the cloud server can rebuild the index without downloading from the docs websites again.
Layout in the bucket: docs/<source path> and code/<technology>/... (the include files).
"""

import argparse
import sys
from pathlib import Path

from docpilot import config
from docpilot.storage.object_store import (
    download_prefix,
    ensure_bucket,
    get_s3_client,
    list_keys,
    upload_folder,
)

# (bucket prefix, local folder): what a fresh machine needs to run 02_ingest.py.
FOLDERS = [("docs/", config.DOCS_DIR), ("code/", config.CODE_DIR)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync the corpus with object storage.")
    parser.add_argument("--download", action="store_true", help="bucket -> laptop")
    parser.add_argument("--to", type=Path, help="with --download: restore under this folder")
    parser.add_argument("--create-buckets", action="store_true", help="create missing buckets")
    args = parser.parse_args()

    s3 = get_s3_client()
    bucket = config.RAW_DOCS_BUCKET
    if args.create_buckets:
        for name in (config.RAW_DOCS_BUCKET, config.SNAPSHOT_BUCKET, config.MLFLOW_BUCKET):
            print(f"{name}: {'created' if ensure_bucket(s3, name) else 'already there'}")
        return

    if args.download:
        for prefix, folder in FOLDERS:
            target = args.to / prefix.rstrip("/") if args.to else folder
            count = download_prefix(s3, bucket, prefix, target)
            print(f"s3://{bucket}/{prefix} -> {target}: {count} files")
        return

    for prefix, folder in FOLDERS:
        if not folder.is_dir():
            sys.exit(f"{folder} not found. Run scripts/01_download_docs.py first.")
        count = upload_folder(s3, folder, bucket, prefix)
        print(f"{folder} -> s3://{bucket}/{prefix}: {count} files")
    print(f"bucket now holds {len(list_keys(s3, bucket))} files")


if __name__ == "__main__":
    main()

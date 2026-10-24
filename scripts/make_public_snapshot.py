"""Pack the PUBLIC part of the main library into one snapshot file (Phase 7 B4, D-066).

The live site must not hold anything marked local_only in ingestion/sources.py (the
learner's interview notes). So, on the laptop:
  1. copy every chunk of the main collection EXCEPT local_only sources into a temporary
     collection (vectors are copied as they are: no re-embedding, same scores),
  2. let Qdrant write a snapshot of it, download it to data/snapshots/ (+ its sha256),
  3. delete the temporary collection and the server-side snapshot.
The server restores the file with `python -m docpilot.store.seed` (see that module).

Run: python -m scripts.make_public_snapshot        (needs the laptop Qdrant in Docker)
"""

import hashlib
import shutil
import sys
import urllib.request
from datetime import UTC, datetime

from qdrant_client import models

from docpilot import config
from docpilot.ingestion.sources import SOURCES
from docpilot.store.qdrant_store import create_collection, get_client

OUT_DIR = config.PROJECT_ROOT / "data" / "snapshots"  # gitignored (data/)
BATCH = 128


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if not config.QDRANT_URL:
        raise SystemExit("Needs Qdrant as a server: set QDRANT_URL in .env (step 3.1)")
    private = sorted(key for key, info in SOURCES.items() if info.visibility != "public")
    keep = models.Filter(
        must_not=[models.FieldCondition(key="technology", match=models.MatchAny(any=private))]
    )
    source, temp = config.COLLECTION_NAME, f"{config.COLLECTION_NAME}_public_tmp"
    client = get_client()
    try:
        if client.collection_exists(temp):
            client.delete_collection(temp)
        create_collection(client, temp, config.EMBEDDING_DIM)  # same layout as the original

        copied, offset = 0, None
        while True:
            points, offset = client.scroll(
                source, scroll_filter=keep, limit=BATCH, offset=offset, with_vectors=True
            )
            client.upsert(
                temp,
                [models.PointStruct(id=p.id, vector=p.vector, payload=p.payload) for p in points],
                wait=True,
            )
            copied += len(points)
            if offset is None:
                break
        total = client.count(source, exact=True).count
        print(f"{source}: {total} chunks; left out {private}: {total - copied}; kept {copied}")

        snapshot = client.create_snapshot(temp, wait=True)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y-%m-%d")
        target = OUT_DIR / f"docpilot_public_{stamp}.snapshot"
        url = f"{config.QDRANT_URL}/collections/{temp}/snapshots/{snapshot.name}"
        with urllib.request.urlopen(url) as response, target.open("wb") as out:
            shutil.copyfileobj(response, out)  # streamed, never all in memory
        client.delete_snapshot(temp, snapshot.name, wait=True)
    finally:
        if client.collection_exists(temp):
            client.delete_collection(temp)  # the laptop keeps only its real collections
        client.close()

    # The seed step passes this checksum to Qdrant, which refuses a damaged file.
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".sha256").write_text(digest + "\n", encoding="utf-8")
    print(f"wrote {target.relative_to(config.PROJECT_ROOT)} ({target.stat().st_size / 1e6:.1f} MB)")
    print(f"sha256 {digest}")


if __name__ == "__main__":
    main()

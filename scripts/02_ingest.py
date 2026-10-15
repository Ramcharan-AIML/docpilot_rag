"""Build the vector index: load docs -> chunk -> embed -> store in Qdrant.

Run: python scripts/02_ingest.py                     (C0: raw text, collection docpilot_naive)
     python scripts/02_ingest.py --clean --collection docpilot_clean   (step 2.2: C0+clean)

Every run starts from an empty collection, so the index always matches the current
docs and settings (CHUNK_SIZE, CHUNK_OVERLAP in config.py).
"""

import argparse
import sys
import time

from docpilot import config
from docpilot.embedding.dense import embed_documents
from docpilot.ingestion.chunkers.fixed import fixed_size_chunks
from docpilot.ingestion.cleaner import clean_markdown
from docpilot.ingestion.loader import load_documents
from docpilot.store.qdrant_store import add_chunks, create_fresh_collection, get_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the vector index.")
    parser.add_argument("--clean", action="store_true", help="remove HTML noise first (2.2)")
    # A separate collection per variant keeps C0 intact, so both can be evaluated.
    parser.add_argument("--collection", default=config.COLLECTION_NAME)
    args = parser.parse_args()
    started = time.perf_counter()

    documents = load_documents(config.DOCS_DIR)
    if not documents:
        # The loader reports facts; the script decides an empty folder is fatal (see 1a.2).
        sys.exit(f"No .md/.txt files in {config.DOCS_DIR}. Run scripts/01_download_docs.py first.")

    chunks = []
    for doc in documents:
        text = clean_markdown(doc.text) if args.clean else doc.text
        doc_chunks = fixed_size_chunks(text, doc.source)
        print(f"{doc.source}: {len(text)} characters -> {len(doc_chunks)} chunks")
        chunks.extend(doc_chunks)

    vectors = embed_documents([chunk.text for chunk in chunks])

    client = get_client(config.QDRANT_PATH)
    try:
        create_fresh_collection(client, args.collection, config.EMBEDDING_DIM)
        add_chunks(client, args.collection, chunks, vectors)
        stored = client.count(args.collection, exact=True).count
    finally:
        client.close()  # release the folder lock even if something above failed

    print(
        f"collection: {args.collection}  cleaned: {args.clean}  documents: {len(documents)}  "
        f"chunks: {len(chunks)}  stored points: {stored}  "
        f"(chunk size {config.CHUNK_SIZE}, overlap {config.CHUNK_OVERLAP})"
    )
    print(f"time: {time.perf_counter() - started:.1f} s")


if __name__ == "__main__":
    main()

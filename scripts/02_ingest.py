"""Build the vector index: load -> (clean) -> (includes) -> chunk -> metadata -> embed -> store.

Run: python scripts/02_ingest.py                     (C0: raw text, collection docpilot_naive)
     python scripts/02_ingest.py --clean --collection docpilot_clean   (step 2.2: C0+clean)
     python scripts/02_ingest.py --clean --includes --collection docpilot_clean_incl  (2.3)

Every run starts from an empty collection, so the index always matches the current
docs and settings (CHUNK_SIZE, CHUNK_OVERLAP in config.py). Metadata (step 2.5) is always
added: it goes into the payload only and does not change the embedded text.
"""

import argparse
import sys
import time

from docpilot import config
from docpilot.embedding.dense import embed_documents
from docpilot.ingestion.chunkers.fixed import fixed_size_chunks
from docpilot.ingestion.chunkers.tokens import MAX_CHUNK_TOKENS, count_tokens
from docpilot.ingestion.cleaner import clean_markdown
from docpilot.ingestion.includes import resolve_includes
from docpilot.ingestion.loader import load_documents
from docpilot.ingestion.metadata import add_metadata, technology_of
from docpilot.store.qdrant_store import add_chunks, create_fresh_collection, get_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the vector index.")
    parser.add_argument("--clean", action="store_true", help="remove HTML noise first (2.2)")
    parser.add_argument(
        "--includes", action="store_true", help="replace {* ... *} markers with code (2.3)"
    )
    # A separate collection per variant keeps C0 intact, so both can be evaluated.
    parser.add_argument("--collection", default=config.COLLECTION_NAME)
    args = parser.parse_args()
    started = time.perf_counter()

    documents = load_documents(config.DOCS_DIR)
    if not documents:
        # The loader reports facts; the script decides an empty folder is fatal (see 1a.2).
        sys.exit(f"No .md/.txt files in {config.DOCS_DIR}. Run scripts/01_download_docs.py first.")

    chunks = []
    resolved_total, missing_total = 0, []
    for doc in documents:
        text = clean_markdown(doc.text) if args.clean else doc.text
        if args.includes:
            code_root = config.CODE_DIR / technology_of(doc.source)
            text, resolved, missing = resolve_includes(text, code_root)
            resolved_total += resolved
            missing_total += missing
        doc_chunks = add_metadata(fixed_size_chunks(text, doc.source), text)
        print(f"{doc.source}: {len(text)} characters -> {len(doc_chunks)} chunks")
        chunks.extend(doc_chunks)
    if args.includes:
        # Missing files are listed, never hidden (run 01_download_docs.py to fetch them).
        print(f"includes resolved: {resolved_total}, missing: {len(missing_total)}")
        for path in missing_total:
            print(f"  missing: {path}")

    # Chunks over the model limit are cut off silently when embedded: report, never hide.
    token_counts = [count_tokens(chunk.text) for chunk in chunks]
    over_limit = sum(count > MAX_CHUNK_TOKENS for count in token_counts)
    print(
        f"chunk tokens: largest {max(token_counts)}, "
        f"over the {MAX_CHUNK_TOKENS}-token limit: {over_limit}"
    )

    vectors = embed_documents([chunk.text for chunk in chunks])

    client = get_client(config.QDRANT_PATH)
    try:
        create_fresh_collection(client, args.collection, config.EMBEDDING_DIM)
        add_chunks(client, args.collection, chunks, vectors)
        stored = client.count(args.collection, exact=True).count
    finally:
        client.close()  # release the folder lock even if something above failed

    print(
        f"collection: {args.collection}  cleaned: {args.clean}  includes: {args.includes}  "
        f"documents: {len(documents)}  chunks: {len(chunks)}  stored points: {stored}  "
        f"(chunk size {config.CHUNK_SIZE}, overlap {config.CHUNK_OVERLAP})"
    )
    print(f"time: {time.perf_counter() - started:.1f} s")


if __name__ == "__main__":
    main()

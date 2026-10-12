"""Build the vector index: load docs -> chunk -> embed -> store in Qdrant.

Run: python scripts/02_ingest.py   (after 01_download_docs.py)

Every run starts from an empty collection, so the index always matches the current
docs and settings (CHUNK_SIZE, CHUNK_OVERLAP in config.py).
"""

import sys
import time

from docpilot import config
from docpilot.chunker import fixed_size_chunks
from docpilot.embedder import embed_documents
from docpilot.loader import load_documents
from docpilot.vector_store import add_chunks, create_fresh_collection, get_client


def main() -> None:
    started = time.perf_counter()

    documents = load_documents(config.DOCS_DIR)
    if not documents:
        # The loader reports facts; the script decides an empty folder is fatal (see 1a.2).
        sys.exit(f"No .md/.txt files in {config.DOCS_DIR}. Run scripts/01_download_docs.py first.")

    chunks = []
    for doc in documents:
        doc_chunks = fixed_size_chunks(doc.text, doc.source)
        print(f"{doc.source}: {len(doc.text)} characters -> {len(doc_chunks)} chunks")
        chunks.extend(doc_chunks)

    vectors = embed_documents([chunk.text for chunk in chunks])

    client = get_client(config.QDRANT_PATH)
    try:
        create_fresh_collection(client, config.COLLECTION_NAME, config.EMBEDDING_DIM)
        add_chunks(client, config.COLLECTION_NAME, chunks, vectors)
        stored = client.count(config.COLLECTION_NAME, exact=True).count
    finally:
        client.close()  # release the folder lock even if something above failed

    print(
        f"documents: {len(documents)}  chunks: {len(chunks)}  stored points: {stored}  "
        f"(chunk size {config.CHUNK_SIZE}, overlap {config.CHUNK_OVERLAP})"
    )
    print(f"time: {time.perf_counter() - started:.1f} s")


if __name__ == "__main__":
    main()

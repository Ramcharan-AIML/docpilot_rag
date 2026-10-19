"""Build the vector index: load -> (clean) -> (includes) -> chunk -> metadata -> embed -> store.

Run: python scripts/02_ingest.py --sources fastapi   (C0: raw text, collection docpilot_naive)
     python scripts/02_ingest.py --clean --includes --strategy recursive --size 400
         --collection docpilot_rec400                 (2.6: one collection per strategy+size)
     strategies: fixed (characters), fixed_tokens, recursive, semantic, parent_child,
     hierarchical, hierarchical_noprefix, qa_pairs, contextual (--base <strategy>, LLM)

Every run starts from an empty collection, so the index always matches the current docs
and settings. Sizes default to config.py (characters for "fixed", tokens for the others).
Metadata (step 2.5) is always added: payload only. The build settings are saved as the
collection's manifest (D-040), which the evals record.
"""

import argparse
import sys
import time
from functools import partial

from docpilot import config
from docpilot.embedding.dense import embed_documents
from docpilot.ingestion.chunkers.base import embedding_text
from docpilot.ingestion.chunkers.contextual import ContextWriter
from docpilot.ingestion.chunkers.fixed import fixed_size_chunks, fixed_token_chunks
from docpilot.ingestion.chunkers.hierarchical import hierarchical_chunks
from docpilot.ingestion.chunkers.parent_child import (
    parent_child_chunks,
    parents_path,
    save_parents,
)
from docpilot.ingestion.chunkers.qa_pairs import qa_pair_chunks
from docpilot.ingestion.chunkers.recursive import recursive_chunks
from docpilot.ingestion.chunkers.semantic import semantic_chunks
from docpilot.ingestion.chunkers.tokens import MAX_CHUNK_TOKENS, count_tokens
from docpilot.ingestion.cleaner import clean_markdown
from docpilot.ingestion.includes import resolve_includes
from docpilot.ingestion.loader import load_documents
from docpilot.ingestion.manifest import save_manifest
from docpilot.ingestion.metadata import add_metadata, technology_of
from docpilot.store.qdrant_store import add_chunks, create_fresh_collection, get_client

TOKENS = config.CHUNK_TOKENS
# name -> (chunk function, size unit, default size, default overlap)
STRATEGIES = {
    "fixed": (fixed_size_chunks, "characters", config.CHUNK_SIZE, config.CHUNK_OVERLAP),
    "fixed_tokens": (fixed_token_chunks, "tokens", TOKENS, config.CHUNK_OVERLAP_TOKENS),
    "recursive": (recursive_chunks, "tokens", TOKENS, config.CHUNK_OVERLAP_TOKENS),
    "semantic": (
        partial(semantic_chunks, percentile_cut=config.SEMANTIC_PERCENTILE),
        "tokens",
        TOKENS,
        0,
    ),
    "parent_child": (parent_child_chunks, "tokens", config.CHILD_TOKENS, 0),
    "hierarchical": (hierarchical_chunks, "tokens", TOKENS, 0),
    "hierarchical_noprefix": (partial(hierarchical_chunks, with_prefix=False), "tokens", TOKENS, 0),
    "qa_pairs": (qa_pair_chunks, "tokens", TOKENS, 0),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the vector index.")
    parser.add_argument("--clean", action="store_true", help="remove HTML noise first (2.2)")
    parser.add_argument(
        "--includes", action="store_true", help="replace {* ... *} markers with code (2.3)"
    )
    parser.add_argument("--strategy", default="fixed", choices=[*sorted(STRATEGIES), "contextual"])
    parser.add_argument(
        "--base",
        default="hierarchical",
        choices=sorted(STRATEGIES),
        help="contextual only: which strategy makes the base chunks",
    )
    parser.add_argument("--size", type=int, help="chunk size (default from config.py)")
    parser.add_argument("--overlap", type=int, help="overlap (default from config.py)")
    # Step 2.7 added PDF/DOCX sources; "--sources fastapi" rebuilds the golden-v0 corpus
    # (the 4 FastAPI pages every row before 2.7 was measured on).
    parser.add_argument("--sources", nargs="+", help="only these sources (default: all)")
    # A separate collection per variant keeps C0 intact, so both can be evaluated.
    parser.add_argument("--collection", default=config.COLLECTION_NAME)
    args = parser.parse_args()
    started = time.perf_counter()

    base = args.base if args.strategy == "contextual" else args.strategy
    chunk_function, unit, default_size, default_overlap = STRATEGIES[base]
    size = args.size if args.size is not None else default_size
    overlap = args.overlap if args.overlap is not None else default_overlap
    parents: dict[str, dict] = {}
    if base == "parent_child":
        chunk_function = partial(parent_child_chunks, parents=parents)
    writer = ContextWriter() if args.strategy == "contextual" else None

    documents = load_documents(config.DOCS_DIR)
    if args.sources:
        documents = [doc for doc in documents if technology_of(doc.source) in args.sources]
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
        doc_chunks = add_metadata(chunk_function(text, doc.source, size, overlap), text)
        if writer is not None:
            writer.add_context(doc_chunks, text)
        print(f"{doc.source}: {len(text)} characters -> {len(doc_chunks)} chunks")
        chunks.extend(doc_chunks)
    if args.includes:
        # Missing files are listed, never hidden (run 01_download_docs.py to fetch them).
        print(f"includes resolved: {resolved_total}, missing: {len(missing_total)}")
        for path in missing_total:
            print(f"  missing: {path}")

    # Chunks over the model limit are cut off silently when embedded: report, never hide.
    token_counts = [count_tokens(embedding_text(chunk)) for chunk in chunks]
    over_limit = sum(count > MAX_CHUNK_TOKENS for count in token_counts)
    print(
        f"chunk tokens (prefix included): largest {max(token_counts)}, "
        f"median {sorted(token_counts)[len(token_counts) // 2]}, "
        f"over the {MAX_CHUNK_TOKENS}-token limit: {over_limit}"
    )

    vectors = embed_documents([embedding_text(chunk) for chunk in chunks])

    client = get_client(config.QDRANT_PATH)
    try:
        create_fresh_collection(client, args.collection, config.EMBEDDING_DIM)
        add_chunks(client, args.collection, chunks, vectors)
        stored = client.count(args.collection, exact=True).count
    finally:
        client.close()  # release the folder lock even if something above failed

    settings = {
        "chunk_strategy": args.strategy,
        "chunk_size": size,
        "chunk_overlap": overlap,
        "chunk_unit": unit,
        "cleaned": args.clean,
        "includes": args.includes,
        "sources": " ".join(args.sources) if args.sources else "all",
        "chunk_count": len(chunks),
        "largest_chunk_tokens": max(token_counts),
        "chunks_over_limit": over_limit,
    }
    if base == "semantic":
        settings["semantic_percentile"] = config.SEMANTIC_PERCENTILE
    if parents:
        path = parents_path(args.collection)
        save_parents(parents, path)
        parent_tokens = sorted(count_tokens(p["text"]) for p in parents.values())
        settings.update(
            parent_max_tokens=config.PARENT_TOKENS,
            parents_file=str(path),
            parent_count=len(parents),
            largest_parent_tokens=parent_tokens[-1],
            median_parent_tokens=parent_tokens[len(parent_tokens) // 2],
        )
    if writer is not None:
        settings.update(
            base_strategy=args.base,
            context_prompt_version=config.CONTEXT_PROMPT_VERSION,
            context_model=writer.model,
            **writer.stats,
        )
        print(f"contextual cost: {writer.stats}")
    manifest = save_manifest(args.collection, settings)
    print(
        f"collection: {args.collection}  strategy: {args.strategy} {size}/{overlap} {unit}  "
        f"cleaned: {args.clean}  includes: {args.includes}  documents: {len(documents)}  "
        f"chunks: {len(chunks)}  stored points: {stored}"
    )
    print(f"manifest: {manifest}")
    print(f"time: {time.perf_counter() - started:.1f} s")


if __name__ == "__main__":
    main()

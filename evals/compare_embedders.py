"""Step 3.7: compare embedding models on the SAME chunks (dense search only, no LLM).

Run:  python -m evals.compare_embedders --models bge-small bge-base --ablation
For each model: read the FT-200 chunks back from the app collection, embed them with the
model, store them in docpilot_emb_<model>, then score the dev questions with dense search.
Dense only, on purpose: hybrid + reranker would hide part of the model's difference.

Plan fix: the plan names this scripts/05_compare_embedders.py; it lives in evals/ with the
other evals so it can reuse their scoring code (`python -m evals.compare_embedders`).

Prefixes are part of each model (model cards checked 2026-10-22). A wrong or missing
prefix quietly lowers scores, the classic bug of embedding comparisons.
"""

import argparse
import time
from collections import defaultdict

import psutil  # RAM of this process (already pinned via accelerate; D-057)
from sentence_transformers import SentenceTransformer

from docpilot import config
from docpilot.ingestion.chunkers.base import Chunk, embedding_text
from docpilot.store.qdrant_store import (
    add_chunks,
    all_payloads,
    create_fresh_collection,
    get_client,
    search,
)
from evals.common import base_record, load_split, save_result
from evals.metrics import percentile
from evals.run_retrieval_eval import SEARCH_K, aggregate, print_table, score_item
from evals.timing import StageTimes
from evals.tracking import log_record

# short name -> model, pinned revision, query prefix, document prefix (Hugging Face, 2026-10-22)
EMBEDDERS = {
    "bge-small": {
        "model": "BAAI/bge-small-en-v1.5",
        "revision": "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
        "query_prefix": config.BGE_QUERY_PREFIX,
        "doc_prefix": "",
    },
    "bge-base": {
        "model": "BAAI/bge-base-en-v1.5",
        "revision": "a5beb1e3e68b9ab74eb54cfd186867f64f240e1a",
        "query_prefix": config.BGE_QUERY_PREFIX,  # same instruction as bge-small
        "doc_prefix": "",
    },
    "bge-m3": {
        "model": "BAAI/bge-m3",
        "revision": "5617a9f61b028005a4858fdac845db406aefb181",
        "query_prefix": "",  # model card: "no longer requires adding instructions"
        "doc_prefix": "",
    },
    "e5-base": {
        "model": "intfloat/e5-base-v2",
        "revision": "f52bf8ec8c7124536f0efb74aca902b2995e5bcd",
        "query_prefix": "query: ",  # model card: every input starts with query: / passage:
        "doc_prefix": "passage: ",
    },
    "nomic": {
        "model": "nomic-ai/nomic-embed-text-v1.5",
        "revision": "e9b6763023c676ca8431644204f50c2b100d9aab",
        # No trust_remote_code needed since transformers 5.5 / sentence-transformers 5.3.
        "query_prefix": "search_query: ",
        "doc_prefix": "search_document: ",
    },
}
MAX_TOKENS = 512  # same cap for all; FT-200 chunks are far below it anyway
SOURCE_COLLECTION = config.COLLECTION_NAME  # FT-200: the chunks every model gets


def ram_mb() -> float:
    return round(psutil.Process().memory_info().rss / 1e6)


def run_model(short: str, chunks: list[Chunk], items: list[dict], ablation: bool) -> None:
    spec = EMBEDDERS[short]
    collection = f"docpilot_emb_{short.replace('-', '_')}"
    ram_before = ram_mb()
    start = time.perf_counter()
    model = SentenceTransformer(spec["model"], revision=spec["revision"])
    model.max_seq_length = min(model.max_seq_length or MAX_TOKENS, MAX_TOKENS)
    load_s = round(time.perf_counter() - start, 1)
    ram_model = ram_mb() - ram_before

    # Index: embed every chunk with this model's document prefix, then store.
    start = time.perf_counter()
    texts = [spec["doc_prefix"] + embedding_text(chunk) for chunk in chunks]
    vectors = model.encode(texts, batch_size=16, normalize_embeddings=True).tolist()
    index_s = round(time.perf_counter() - start, 1)
    dim = len(vectors[0])

    client = get_client()
    rows, times = [], StageTimes()
    try:
        create_fresh_collection(client, collection, dim)
        add_chunks(client, collection, chunks, vectors)
        model.encode(spec["query_prefix"] + "warm-up")  # first call is a cold number
        for item in items:
            with times.measure("embed"):
                query = spec["query_prefix"] + item["question"]
                vector = model.encode(query, normalize_embeddings=True).tolist()
            with times.measure("search"):
                hits = search(client, collection, vector, SEARCH_K)
            rows.append(score_item(item, hits))
    finally:
        client.close()

    by_type, by_domain = defaultdict(list), defaultdict(list)
    for row in rows:
        by_type[row["type"]].append(row)
        by_domain[row["domain"]].append(row)
    record = base_record(f"E-{short}", "dev", "retrieval", SOURCE_COLLECTION)
    record["collection"] = collection
    record["settings"].update(
        {
            "retriever": "dense",
            "search_k": SEARCH_K,
            "embedding_model": spec["model"],
            "embedding_revision": spec["revision"],
            "embedding_dim": dim,
            "query_prefix": spec["query_prefix"],
            "doc_prefix": spec["doc_prefix"],
            "chunks_from": SOURCE_COLLECTION,
        }
    )
    record["overall"] = aggregate(rows)
    record["per_type"] = {name: aggregate(group) for name, group in sorted(by_type.items())}
    record["per_domain"] = {name: aggregate(group) for name, group in sorted(by_domain.items())}
    stages = times.summary()
    record["search_latency_ms"] = stages["search"]
    record["stage_latency_ms"] = stages
    record["embedder_cost"] = {
        "dim": dim,
        "chunks": len(chunks),
        "load_s": load_s,
        "index_s": index_s,
        "ram_model_mb": ram_model,  # process RAM growth while loading (approximate)
        "query_embed_p50_ms": percentile(times.times["embed"], 50),
    }
    record["per_question"] = rows
    print_table(record)
    cost = record["embedder_cost"]
    print(f"  dim {dim}, load {load_s} s, index {index_s} s for {len(chunks)} chunks, ", end="")
    print(f"RAM +{ram_model} MB")
    path = save_result(record)
    run_id = log_record(record, path, ablation=ablation)
    print(f"saved {path}; MLflow run {run_id}; cost {cost}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare embedding models (dense, dev split).")
    parser.add_argument("--models", nargs="+", default=list(EMBEDDERS), choices=list(EMBEDDERS))
    parser.add_argument("--ablation", action="store_true", help="mark rows for ABLATION.md")
    args = parser.parse_args()

    items = [item for item in load_split("dev") if item["should_answer"]]
    client = get_client()
    try:
        chunks = [Chunk(**payload) for payload in all_payloads(client, SOURCE_COLLECTION)]
    finally:
        client.close()
    # Same order every run (scroll order is by point id, but do not rely on it).
    chunks.sort(key=lambda chunk: (chunk.source, chunk.chunk_number))
    print(f"{len(chunks)} chunks from {SOURCE_COLLECTION}")
    for short in args.models:
        print(f"\n=== {short}: {EMBEDDERS[short]['model']}")
        run_model(short, chunks, items, args.ablation)


if __name__ == "__main__":
    main()

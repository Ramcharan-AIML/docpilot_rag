"""Helpers shared by the eval runners: load a split, label a result, save it, retry an ask."""

import json
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

from openai import OpenAI, RateLimitError
from qdrant_client import QdrantClient

from docpilot import config
from docpilot.ingestion.manifest import load_manifest
from docpilot.rag import ask, elapsed_ms
from evals.validate_golden import GOLDEN_DIR, check_item, check_snippets, load_items, validate

RESULTS_DIR = Path(__file__).resolve().parent / "results"
# Bump evals/golden/VERSION when questions, evidence or the corpus change (history in
# evals/golden/README.md: v0 = 32 items on 4 FastAPI pages ... v1 = 65 items, 3 domains).
GOLDEN_VERSION = (GOLDEN_DIR / "VERSION").read_text(encoding="utf-8").strip()


def load_split(split: str) -> list[dict]:
    """Validate the whole golden set first, then return one split.

    Scoring against a broken answer key gives a wrong number that looks right, so a
    validation error stops the run.
    """
    _, errors = validate(GOLDEN_DIR, config.DOCS_DIR)
    if errors:
        sys.exit("Golden set invalid; run: python evals/validate_golden.py")
    items, _ = load_items(GOLDEN_DIR / f"{split}.jsonl")
    return items


def load_golden_file(path: Path) -> list[dict]:
    """A golden file outside dev/test (the CI gate's ci.jsonl), checked with the same rules.

    Its snippets are checked against config.DOCS_DIR, which the gate points at the fixture
    corpus. An invalid file stops the run, like load_split.
    """
    items, errors = load_items(path)
    split = path.stem  # ci.jsonl -> every item must say "split": "ci"
    for item in items:
        item_errors = check_item(item, split)
        errors += item_errors or check_snippets(item, config.DOCS_DIR)
    if errors:
        sys.exit(f"{path.name} invalid:\n  " + "\n  ".join(errors))
    return items


def git_commit() -> str:
    """Short commit id, plus '+dirty' if there are uncommitted changes.

    '+dirty' warns that the code that produced a number is not exactly any commit.
    New result files in evals/results/ are ignored: they are outputs, not code, and
    counting them made the second of two back-to-back runs "+dirty" (2026-10-17).
    The LLM cache in evals/cache/ (step 3.6) is an output too: the first transform run
    writes it, and must not mark its own result "+dirty". Same for evals/spot_checks/ (3.9).
    """
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    changes = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "--",
            ".",
            ":(exclude)evals/results",
            ":(exclude)evals/cache",
            ":(exclude)evals/spot_checks",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return commit + ("+dirty" if changes else "")


def base_record(
    config_id: str, split: str, kind: str, collection: str = config.COLLECTION_NAME
) -> dict:
    """The labels every result file carries, so a number can always be traced back.

    Chunk settings come from the collection's manifest (written by 02_ingest.py), because
    each collection can be built differently. Collections built before manifests existed
    fall back to config.py, and the record says so.
    """
    record = {
        "kind": kind,  # "retrieval", "latency" or "abstention"
        "config_id": config_id,
        "collection": collection,
        "split": split,
        "date": date.today().isoformat(),
        "git_commit": git_commit(),
        "settings": {
            "golden_version": GOLDEN_VERSION,  # scores are comparable only on the same set
            "chunk_strategy": config.CHUNK_STRATEGY,
            "chunk_size": config.CHUNK_SIZE,
            "chunk_overlap": config.CHUNK_OVERLAP,
            "embedding_model": config.EMBEDDING_MODEL,
            "embedding_revision": config.EMBEDDING_REVISION,
            "answer_top_k": config.TOP_K,  # chunks given to the LLM in ask()
        },
    }
    manifest = load_manifest(collection)
    record["settings"]["settings_source"] = "manifest" if manifest else "config.py"
    if manifest:
        record["settings"].update(manifest)
    return record


def to_json(record: dict) -> str:
    """Pretty JSON, but each per_question row on ONE line.

    Fully indented, one result file reached 744 lines (every list item on its own line),
    breaking the 500-line rule; one row per line is also easier to scan and diff.
    """
    head = {key: value for key, value in record.items() if key != "per_question"}
    text = json.dumps(head, indent=2, ensure_ascii=False)
    rows = record.get("per_question", [])
    if not rows:
        return text + "\n"
    lines = ",\n".join("    " + json.dumps(row, ensure_ascii=False) for row in rows)
    return text[:-2] + ',\n  "per_question": [\n' + lines + "\n  ]\n}\n"  # text ends "\n}"


def save_result(record: dict) -> Path:
    """Write evals/results/<date>_<config>_<split>_<kind>.json and return the path."""
    RESULTS_DIR.mkdir(exist_ok=True)
    name = f"{record['date']}_{record['config_id']}_{record['split']}_{record['kind']}.json"
    path = RESULTS_DIR / name
    path.write_text(to_json(record), encoding="utf-8")
    return path


def ask_with_retries(
    question: str,
    qdrant_client: QdrantClient,
    llm_client: OpenAI,
    max_attempts: int = 4,
    collection: str = config.COLLECTION_NAME,
) -> dict:
    """Run ask() and count rate-limit (429) retries ourselves.

    The openai library normally retries 429 silently (max_retries=2), which would hide
    them. We switch that off and retry here, so retries are counted and their waiting
    time shows up in `wall_ms` (D-031: retries are part of the slow tail).
    """
    counted_client = llm_client.with_options(max_retries=0)
    start = time.perf_counter()
    for attempt in range(1, max_attempts + 1):
        try:
            result = ask(question, qdrant_client, counted_client, collection)
            return {**result, "retries_429": attempt - 1, "wall_ms": elapsed_ms(start)}
        except RateLimitError as error:
            if attempt == max_attempts:
                raise
            # Use the server's hint when it gives one; otherwise wait a little longer each time.
            wait = float(error.response.headers.get("retry-after", 2 * attempt))
            print(f"  429 rate limit, waiting {wait:.0f} s (attempt {attempt})")
            time.sleep(wait)
    raise AssertionError("unreachable")  # the loop either returns or raises

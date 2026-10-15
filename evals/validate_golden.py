"""Check the golden dataset before any eval uses it.

Run: python evals/validate_golden.py

A typo in one snippet silently turns a hit into a miss and lowers every score, so this
runs after EVERY edit of evals/golden/*.jsonl. Exit code 1 means "fix the file first".
"""

import json
import sys
from collections import Counter
from pathlib import Path

from docpilot import config

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
SPLITS = ("dev", "test")
REQUIRED_FIELDS = (
    "id",
    "question",
    "type",
    "should_answer",
    "reference_answer",
    "evidence",
    "difficulty",
    "split",
    "notes",
)
# Question types from PROJECT_DOCUMENTATION section 2 that the 4 Phase 1 pages can test.
# The others (version-specific, concept, interview, adversarial, risky) need other
# documents or guardrails and join in later phases (see evals/golden/README.md).
TYPES = (
    "factual",
    "how-to",
    "exact-identifier",
    "paraphrase",
    "comparison",
    "multi-hop",
    "table-or-code",
    "not-in-docs",
)
DIFFICULTIES = ("easy", "medium", "hard")


def load_items(path: Path) -> tuple[list[dict], list[str]]:
    """Read one JSONL file. Returns (items, errors); a broken line is an error, not a crash."""
    items, errors = [], []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue  # blank lines are allowed, they carry no item
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError as error:
            errors.append(f"{path.name} line {line_number}: not valid JSON ({error.msg})")
    return items, errors


def check_item(item: dict, expected_split: str) -> list[str]:
    """Rules for one item that need no documents: fields, allowed values, consistency."""
    label = item.get("id", "<no id>")
    missing = [field for field in REQUIRED_FIELDS if field not in item]
    if missing:
        return [f"{label}: missing fields {missing}"]  # the checks below need the fields

    errors = []
    if item["type"] not in TYPES:
        errors.append(f"{label}: type {item['type']!r} not in {TYPES}")
    if item["difficulty"] not in DIFFICULTIES:
        errors.append(f"{label}: difficulty {item['difficulty']!r} not in {DIFFICULTIES}")
    if item["split"] != expected_split:
        errors.append(f"{label}: split is {item['split']!r} but it is in {expected_split}.jsonl")
    if not item["question"].strip():
        errors.append(f"{label}: empty question")

    # An answerable question needs proof; an unanswerable one must have none.
    if item["should_answer"] and not item["evidence"]:
        errors.append(f"{label}: should_answer is true but evidence is empty")
    if not item["should_answer"] and item["evidence"]:
        errors.append(f"{label}: should_answer is false but evidence is not empty")
    if (item["type"] == "not-in-docs") == bool(item["should_answer"]):
        errors.append(f"{label}: type not-in-docs must go with should_answer false (and only it)")

    for evidence in item["evidence"]:
        if "\n" in evidence.get("snippet", ""):
            errors.append(f"{label}: snippet spans lines; keep it to one line")
    return errors


def check_snippets(item: dict, docs_dir: Path) -> list[str]:
    """Every snippet must appear EXACTLY (character for character) in its raw document."""
    errors = []
    for evidence in item["evidence"]:
        doc_path = docs_dir / evidence["doc"]
        if not doc_path.is_file():
            errors.append(f"{item['id']}: document {evidence['doc']} not found in {docs_dir}")
            continue
        if evidence["snippet"] not in doc_path.read_text(encoding="utf-8"):
            snippet = evidence["snippet"]
            errors.append(f"{item['id']}: snippet not in {evidence['doc']}: {snippet!r}")
    return errors


def validate(golden_dir: Path, docs_dir: Path) -> tuple[list[dict], list[str]]:
    """Validate dev and test together (ids must be unique across both files)."""
    all_items, errors = [], []
    for split in SPLITS:
        path = golden_dir / f"{split}.jsonl"
        if not path.is_file():
            errors.append(f"missing file {path}")
            continue
        items, load_errors = load_items(path)
        errors += load_errors
        for item in items:
            item_errors = check_item(item, split)
            errors += item_errors
            if not item_errors:
                errors += check_snippets(item, docs_dir)
        all_items += items

    id_counts = Counter(item.get("id") for item in all_items)
    errors += [f"duplicate id {item_id}" for item_id, n in id_counts.items() if n > 1]
    return all_items, errors


def print_summary(items: list[dict]) -> None:
    """Counts per split and type, so an unbalanced split is easy to see."""
    print(f"{len(items)} items")
    for split in SPLITS:
        in_split = [item for item in items if item["split"] == split]
        unanswerable = sum(not item["should_answer"] for item in in_split)
        types = Counter(item["type"] for item in in_split)
        print(f"  {split}: {len(in_split)} items, {unanswerable} unanswerable, {dict(types)}")


def main() -> None:
    if not config.DOCS_DIR.is_dir():
        sys.exit(f"{config.DOCS_DIR} not found. Run scripts/01_download_docs.py first.")
    items, errors = validate(GOLDEN_DIR, config.DOCS_DIR)
    if errors:
        print("\n".join(errors))
        sys.exit(f"FAILED: {len(errors)} problem(s)")
    print_summary(items)
    print("OK: all fields valid, ids unique, every snippet found in its document")


if __name__ == "__main__":
    main()

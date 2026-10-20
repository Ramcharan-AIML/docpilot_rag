"""Step 2.9: build and score every chunking config on the dev split, then regenerate ABLATION.md.

Run: python scripts/run_chunking_matrix.py              (all configs without LLM calls)
     python scripts/run_chunking_matrix.py --dry-run    (only print the commands)
     python scripts/run_chunking_matrix.py --only C4-200-v1 C1-400-v1
     python scripts/run_chunking_matrix.py --with-llm   (adds C5 contextual: 1 LLM call
                                                         per chunk, Groq free-tier limits)

For each config it runs exactly the two commands you would type by hand (02_ingest.py, then
evals.run_retrieval_eval --ablation), so the matrix and a manual run cannot disagree.
A config already scored on this commit and golden version is skipped, so an interrupted
matrix can simply be started again. Stop uvicorn first: local Qdrant allows one process.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "evals" / "results"
GOLDEN_VERSION = (PROJECT_ROOT / "evals" / "golden" / "VERSION").read_text().strip()
SPLIT = "dev"  # the test split is run once, by hand, for the winner and C0 only


def recipe(strategy: str, size: int, overlap: int | None = None, raw: bool = False) -> list[str]:
    """02_ingest.py arguments. Every config but C0 is cleaned and has its includes resolved."""
    args = [] if raw else ["--clean", "--includes"]
    args += ["--strategy", strategy, "--size", str(size)]
    return args + (["--overlap", str(overlap)] if overlap is not None else [])


# (config id, collection, 02_ingest.py arguments). C0 stays raw (the frozen naive
# baseline); the FT rows are the fair control: fixed-size chunks WITH cleaning and
# includes, so C1-C4 are compared on chunking alone (cake rule: one change at a time).
MATRIX = [
    ("C0-v1", "docpilot_v1_c0", recipe("fixed", 800, 100, raw=True)),
    ("FT-200-v1", "docpilot_v1_ft200", recipe("fixed_tokens", 200, 25)),
    ("FT-400-v1", "docpilot_v1_ft400", recipe("fixed_tokens", 400, 50)),
    ("C1-200-v1", "docpilot_v1_rec200", recipe("recursive", 200, 25)),
    ("C1-400-v1", "docpilot_v1_rec400", recipe("recursive", 400, 50)),
    ("C2-400-v1", "docpilot_v1_sem400", recipe("semantic", 400)),
    ("C3-128-v1", "docpilot_v1_pc128", recipe("parent_child", 128)),
    ("C4-200-v1", "docpilot_v1_hier200", recipe("hierarchical", 200)),
    ("C4-400-v1", "docpilot_v1_hier400", recipe("hierarchical", 400)),
    ("C4-400-noprefix-v1", "docpilot_v1_hier400np", recipe("hierarchical_noprefix", 400)),
    ("QA-400-v1", "docpilot_v1_qa400", recipe("qa_pairs", 400)),
]
# Costs one LLM call per chunk (cached afterwards), so it only runs when asked for.
LLM_MATRIX = [
    ("C5-200-v1", "docpilot_v1_ctx200", [*recipe("contextual", 200), "--base", "hierarchical"]),
]


def git_state() -> tuple[str, bool]:
    """(short commit, dirty?). Result files are outputs, not code, so they do not count."""
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    changes = subprocess.run(
        ["git", "status", "--porcelain", "--", ".", ":(exclude)evals/results"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return commit, bool(changes)


def is_done(config_id: str, commit: str, results_dir: Path = RESULTS_DIR) -> bool:
    """True if a dev result for this config exists from this commit and golden version."""
    for path in results_dir.glob(f"*_{config_id}_{SPLIT}_retrieval.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        same_exam = record["settings"].get("golden_version") == GOLDEN_VERSION
        if same_exam and record["git_commit"] == commit:
            return True
    return False


def commands(config_id: str, collection: str, ingest_args: list[str]) -> list[list[str]]:
    """The two commands for one config: build the collection, then score it."""
    ingest = [sys.executable, "scripts/02_ingest.py", *ingest_args, "--collection", collection]
    evaluate = [
        sys.executable, "-m", "evals.run_retrieval_eval", "--collection", collection,
        "--split", SPLIT, "--config-id", config_id, "--ablation",
    ]  # fmt: skip
    return [ingest, evaluate]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the chunking matrix (plan step 2.9).")
    parser.add_argument("--only", nargs="+", help="only these config ids")
    parser.add_argument("--with-llm", action="store_true", help="also run C5 contextual")
    parser.add_argument("--force", action="store_true", help="re-run configs already done")
    parser.add_argument("--allow-dirty", action="store_true", help="run on uncommitted code")
    parser.add_argument("--dry-run", action="store_true", help="print the commands only")
    args = parser.parse_args()

    configs = MATRIX + (LLM_MATRIX if args.with_llm else [])
    if args.only:
        unknown = set(args.only) - {config_id for config_id, _, _ in MATRIX + LLM_MATRIX}
        if unknown:
            sys.exit(f"unknown config ids: {sorted(unknown)}")
        configs = [c for c in MATRIX + LLM_MATRIX if c[0] in args.only]

    commit, dirty = git_state()
    if dirty and not (args.allow_dirty or args.dry_run):
        # A "+dirty" number cannot be traced to any commit, so it cannot go in the table.
        sys.exit("Uncommitted changes: commit first (or --allow-dirty for a trial run).")

    started = time.perf_counter()
    for config_id, collection, ingest_args in configs:
        if not args.force and is_done(config_id, commit):
            print(f"== {config_id}: already scored on {commit} (golden {GOLDEN_VERSION}), skipped")
            continue
        print(f"\n== {config_id} ({collection})")
        for command in commands(config_id, collection, ingest_args):
            print("   $ " + " ".join(command[1:]))
            if not args.dry_run:
                # check=True: a failed step stops the matrix instead of scoring a stale index.
                subprocess.run(command, cwd=PROJECT_ROOT, check=True)

    if not args.dry_run:
        subprocess.run([sys.executable, "-m", "evals.make_ablation"], cwd=PROJECT_ROOT, check=True)
        print(f"\nmatrix time: {(time.perf_counter() - started) / 60:.1f} min")


if __name__ == "__main__":
    main()

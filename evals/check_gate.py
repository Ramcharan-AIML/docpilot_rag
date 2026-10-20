"""The CI eval gate's judge (step 2.10, D-011): did retrieval get worse than the baseline?

Run: python -m evals.check_gate RESULT.json                  (exit 0 = pass, 1 = fail)
     python -m evals.check_gate RESULT.json --update --reason "why the new numbers are right"

RESULT.json is a retrieval result on evals/golden/ci.jsonl (made by scripts/ci_gate.py).
It fails if Recall@5 or MRR is below  baseline - tolerance. Updating the baseline is a
deliberate act: --update needs a reason, and the pull request that changes
evals/baseline_ci.json must say why (an improvement was kept, or the fixture changed).
"""

import argparse
import json
import sys
from pathlib import Path

BASELINE_FILE = Path(__file__).resolve().parent / "baseline_ci.json"
GATED_METRICS = ("recall@5", "mrr")
# Allowed wobble below the baseline. With 18 questions, one question = 0.056 of Recall@5,
# and one answer slipping from rank 1 to rank 2 costs 0.028 of MRR. The gate forgives about
# one such small slip (tiny float differences between Windows and the Linux CI runner can
# flip a near-tie) but not a real break: the units bug measured 2026-10-20 (fixed, 200
# characters instead of tokens) dropped Recall@5 by 0.222 and MRR by 0.375.
DEFAULT_TOLERANCE = {"recall@5": 0.06, "mrr": 0.05}
WHY_TOLERANCE = (
    "about one question of wobble (cross-platform float near-ties); measured breaks drop "
    "Recall@5 by 0.17-0.33 and MRR by 0.37-0.39 (D-048)"
)


def compare(overall: dict, baseline: dict) -> list[dict]:
    """One row per gated metric: baseline, now, the lowest allowed value, pass or fail."""
    rows = []
    for name in GATED_METRICS:
        floor = round(baseline["metrics"][name] - baseline["tolerance"][name], 3)
        rows.append(
            {
                "metric": name,
                "baseline": baseline["metrics"][name],
                "now": overall[name],
                "floor": floor,
                "passed": overall[name] >= floor,
            }
        )
    return rows


def new_baseline(record: dict, old: dict | None, reason: str) -> dict:
    """The current scores become the baseline; tolerances are kept (they have their own why)."""
    settings = record["settings"]
    return {
        "golden_file": "evals/golden/ci.jsonl",
        "metrics": {name: record["overall"][name] for name in GATED_METRICS},
        "n": record["overall"]["n"],
        "tolerance": old["tolerance"] if old else DEFAULT_TOLERANCE,
        "why_tolerance": old["why_tolerance"] if old else WHY_TOLERANCE,
        "made_from": {
            "git_commit": record["git_commit"],
            "date": record["date"],
            "chunking": f"{settings['chunk_strategy']} {settings['chunk_size']}",
        },
        "reason": reason,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fail if retrieval fell below the baseline.")
    parser.add_argument("result", type=Path, help="retrieval result JSON on ci.jsonl")
    parser.add_argument("--baseline", type=Path, default=BASELINE_FILE)
    parser.add_argument("--update", action="store_true", help="make this result the baseline")
    parser.add_argument("--reason", default="", help="required with --update")
    args = parser.parse_args()

    record = json.loads(args.result.read_text(encoding="utf-8"))
    old = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline.exists() else None

    if args.update:
        if not args.reason.strip():
            sys.exit("--update needs --reason: a baseline change must say why")
        baseline = new_baseline(record, old, args.reason)
        args.baseline.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
        print(f"baseline updated: {baseline['metrics']} ({args.baseline.name})")
        return
    if old is None:
        sys.exit(f"no baseline at {args.baseline}; create one with --update --reason ...")

    rows = compare(record["overall"], old)
    print(f"\nCI eval gate ({record['overall']['n']} questions, commit {record['git_commit']})")
    print(f"{'metric':10}{'baseline':>10}{'now':>10}{'floor':>10}  result")
    for row in rows:
        verdict = "PASS" if row["passed"] else "FAIL"
        print(
            f"{row['metric']:10}{row['baseline']:>10}{row['now']:>10}{row['floor']:>10}  {verdict}"
        )
    if not all(row["passed"] for row in rows):
        # Exit code 1 is what turns the GitHub check red.
        sys.exit("\nGate FAILED: retrieval got worse than the baseline (see the table above).")
    print("\nGate passed.")


if __name__ == "__main__":
    main()

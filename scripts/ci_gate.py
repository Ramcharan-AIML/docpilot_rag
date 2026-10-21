"""Step 2.10: the CI eval gate in one command, the same on GitHub and on the laptop.

Run: python scripts/ci_gate.py                         (exit 0 = pass, 1 = fail)
     python scripts/ci_gate.py --result ci_gate_result.json   (keep the result file)
     python scripts/ci_gate.py --update-baseline "why"  (make this run the new baseline)

Three steps, each the real command the project uses:
1. ingest the fixture corpus (tests/fixtures/corpus/) with the app's own recipe
   (config.INGEST_ARGS), into a temporary Qdrant folder: the laptop's index is never touched;
2. score evals/golden/ci.jsonl with the retrieval eval (no LLM, no API key);
3. evals/check_gate.py compares Recall@5 and MRR with evals/baseline_ci.json.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from docpilot import config

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DOCS = PROJECT_ROOT / "tests" / "fixtures" / "corpus"
CI_GOLDEN = PROJECT_ROOT / "evals" / "golden" / "ci.jsonl"
COLLECTION = "ci_gate"


def run(step: str, command: list[str], env: dict) -> int:
    print(f"\n== {step}\n   $ {' '.join(command[1:])}", flush=True)
    return subprocess.run(command, cwd=PROJECT_ROOT, env=env).returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CI retrieval eval gate.")
    parser.add_argument("--result", type=Path, help="also keep the result JSON here")
    parser.add_argument("--update-baseline", metavar="REASON", help="save as the new baseline")
    args = parser.parse_args()

    work = Path(tempfile.mkdtemp(prefix="docpilot_ci_gate_"))
    result = args.result.resolve() if args.result else work / "ci_result.json"
    # Moves the docs, the index and the manifests for the child processes only (config.py).
    env = {
        **os.environ,
        "DOCPILOT_DOCS_DIR": str(FIXTURE_DOCS),
        "DOCPILOT_QDRANT_PATH": str(work / "qdrant"),
        "DOCPILOT_MANIFEST_DIR": str(work / "manifests"),
        "QDRANT_URL": "",  # always local mode: never write the gate's index into Docker Qdrant
    }
    python = sys.executable
    gate = [python, "-m", "evals.check_gate", str(result)]
    if args.update_baseline:
        gate += ["--update", "--reason", args.update_baseline]
    steps = [
        ("1/3 ingest the fixture corpus (app recipe)",
         [python, "scripts/02_ingest.py", *config.INGEST_ARGS, "--collection", COLLECTION]),
        ("2/3 retrieval eval on ci.jsonl",
         [python, "-m", "evals.run_retrieval_eval", "--collection", COLLECTION,
          "--golden", str(CI_GOLDEN), "--config-id", "CI-gate", "--output", str(result)]),
        ("3/3 compare with the baseline", gate),
    ]  # fmt: skip
    try:
        for step, command in steps:
            code = run(step, command, env)
            if code != 0:
                sys.exit(code)  # the first failing step decides; CI shows its output above
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()

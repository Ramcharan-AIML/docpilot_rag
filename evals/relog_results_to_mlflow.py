"""Copy saved eval results (evals/results/*.json) into MLflow, so old runs sit next to new ones.

Run: python -m evals.relog_results_to_mlflow            (all C0 files)
     python -m evals.relog_results_to_mlflow "*C1*"     (any glob pattern)
Numbers are read from the JSON files, never typed. A file that is already logged is skipped.
"""

import json
import sys

from evals.common import RESULTS_DIR
from evals.tracking import log_record

# Result files written before step 2.0 have no golden_version / chunk_strategy in their
# settings. For them the true values are known: golden set v0 was the only version, and
# C0 is the fixed-size chunker (D-006). Files that have the fields keep their own values.
PRE_2_0_DEFAULTS = {"golden_version": "v0", "chunk_strategy": "fixed"}


def main() -> None:
    pattern = sys.argv[1] if len(sys.argv) > 1 else "*C0*"
    paths = sorted(RESULTS_DIR.glob(f"{pattern}.json"))
    if not paths:
        sys.exit(f"no result files match {pattern!r} in {RESULTS_DIR}")
    for path in paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        for key, value in PRE_2_0_DEFAULTS.items():
            record["settings"].setdefault(key, value)
        # The baseline runs are the C0 row of the ablation table.
        run_id = log_record(record, path, ablation=record["config_id"] == "C0")
        status = f"logged as run {run_id}" if run_id else "already logged, skipped"
        print(f"{path.name}: {status}")


if __name__ == "__main__":
    main()

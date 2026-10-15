"""Log eval results to MLflow, the searchable "lab notebook" of experiments (D-022, D-036).

The results JSON in evals/results/ stays the committed source of truth; MLflow is the
index on top of it: one run per result file, with params (the recipe), metrics (the
scores), tags (labels) and the JSON itself attached. Browse with:  mlflow ui
"""

from pathlib import Path

import mlflow

from docpilot import config

# One experiment (notebook) per kind of eval, so retrieval runs are compared with
# retrieval runs only.
EXPERIMENT_PREFIX = "docpilot-"


def metric_name(name: str) -> str:
    """MLflow names cannot contain '@': 'recall@5' -> 'recall_at_5'."""
    return name.replace("@", "_at_")


def params_and_metrics(record: dict) -> tuple[dict, dict]:
    """Split one result record into params (inputs) and metrics (numbers to compare)."""
    params = {**record["settings"], "collection": record["collection"], "split": record["split"]}
    metrics: dict[str, float] = {}

    if record["kind"] == "retrieval":
        for name, value in record["overall"].items():
            metrics[metric_name(name)] = value  # includes n (questions scored)
        for qtype, summary in record["per_type"].items():
            # Only the two headline numbers per type: the full table is in the JSON.
            metrics[f"type_{qtype}_recall_at_5"] = summary["recall@5"]
            metrics[f"type_{qtype}_mrr"] = summary["mrr"]
        metrics["search_p50_ms"] = record["search_latency_ms"]["p50"]
        metrics["search_p95_ms"] = record["search_latency_ms"]["p95"]
    elif record["kind"] == "latency":
        for stage, summary in record["per_stage_ms"].items():
            metrics[f"{stage}_p50_ms"] = summary["p50"]
            metrics[f"{stage}_p95_ms"] = summary["p95"]
        metrics["n"] = record["per_stage_ms"]["total"]["n"]
        metrics["retries_429"] = record["retries_429_total"]
    elif record["kind"] == "abstention":
        metrics.update(record["overall"])
    else:
        raise ValueError(f"unknown result kind {record['kind']!r}")
    return params, metrics


def get_experiment_id(name: str) -> str:
    """Find the experiment, or create it with our artifact folder (not MLflow's default)."""
    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    experiment = mlflow.get_experiment_by_name(name)
    if experiment is not None:
        return experiment.experiment_id
    return mlflow.create_experiment(name, artifact_location=config.MLFLOW_ARTIFACT_DIR.as_uri())


def is_logged(experiment_id: str, results_file: str) -> bool:
    """True if this result file already has a run, so re-logging never makes duplicates."""
    runs = mlflow.search_runs(
        experiment_ids=[experiment_id],
        filter_string=f"tags.results_file = '{results_file}'",
        output_format="list",
    )
    return bool(runs)


def log_record(record: dict, results_path: Path, ablation: bool = False) -> str | None:
    """Log one saved result file as one MLflow run. Returns the run id, or None if the file
    was logged before. `ablation=True` marks runs that belong in evals/ABLATION.md."""
    experiment_id = get_experiment_id(EXPERIMENT_PREFIX + record["kind"])
    if is_logged(experiment_id, results_path.name):
        return None
    params, metrics = params_and_metrics(record)
    tags = {
        "config_id": record["config_id"],
        "git_commit": record["git_commit"],
        "date": record["date"],
        "split": record["split"],
        "results_file": results_path.name,  # the link back to the committed JSON
        "ablation": str(ablation).lower(),
    }
    with mlflow.start_run(experiment_id=experiment_id, run_name=record["config_id"]) as run:
        mlflow.set_tags(tags)
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.log_artifact(str(results_path))  # the full JSON, per-question rows included
    return run.info.run_id

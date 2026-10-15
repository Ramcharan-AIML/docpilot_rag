"""Tests for evals/tracking.py. MLflow writes to a temporary SQLite file, never mlflow.db."""

import json

import mlflow
import pytest

from docpilot import config
from evals.tracking import log_record, metric_name, params_and_metrics


def retrieval_record() -> dict:
    """A made-up retrieval result in the same shape run_retrieval_eval.py saves."""
    return {
        "kind": "retrieval",
        "config_id": "T0",
        "collection": "demo",
        "split": "dev",
        "date": "2026-10-15",
        "git_commit": "abc1234",
        "settings": {"golden_version": "v0", "chunk_strategy": "fixed", "chunk_size": 800},
        "overall": {"n": 2, "recall@5": 0.5, "mrr": 0.25},
        "per_type": {"how-to": {"n": 2, "recall@5": 0.5, "mrr": 0.25}},
        "search_latency_ms": {"n": 2, "p50": 1.0, "p95": 2.0},
        "per_question": [],
    }


def test_metric_name_removes_at_sign():
    assert metric_name("recall@5") == "recall_at_5"
    assert metric_name("mrr") == "mrr"


def test_retrieval_record_splits_into_params_and_metrics():
    params, metrics = params_and_metrics(retrieval_record())
    assert params["chunk_strategy"] == "fixed" and params["split"] == "dev"
    assert metrics["recall_at_5"] == 0.5
    assert metrics["type_how-to_mrr"] == 0.25
    assert metrics["search_p95_ms"] == 2.0


def test_unknown_kind_fails_loudly():
    record = {**retrieval_record(), "kind": "mystery"}
    with pytest.raises(ValueError):
        params_and_metrics(record)


@pytest.fixture
def temp_mlflow(tmp_path, monkeypatch):
    """Point tracking at a throwaway database and artifact folder."""
    monkeypatch.setattr(config, "MLFLOW_TRACKING_URI", f"sqlite:///{tmp_path.as_posix()}/t.db")
    monkeypatch.setattr(config, "MLFLOW_ARTIFACT_DIR", tmp_path / "artifacts")
    return tmp_path


def test_log_record_copies_numbers_exactly_and_never_twice(temp_mlflow):
    path = temp_mlflow / "2026-10-15_T0_dev_retrieval.json"
    record = retrieval_record()
    path.write_text(json.dumps(record), encoding="utf-8")

    run_id = log_record(record, path, ablation=True)
    assert run_id is not None
    run = mlflow.get_run(run_id)
    assert run.data.metrics["recall_at_5"] == 0.5  # same value as the JSON
    assert run.data.params["chunk_size"] == "800"  # MLflow stores params as text
    assert run.data.tags["ablation"] == "true"
    assert run.data.tags["results_file"] == path.name

    assert log_record(record, path) is None  # second time: skipped, no duplicate run

"""Tests for evals/make_ablation.py and scripts/run_chunking_matrix.py, on made-up records."""

import json

import pytest

from evals.make_ablation import (
    END,
    START,
    latest_per_config,
    main_table,
    per_domain_table,
    replace_block,
)
from scripts.run_chunking_matrix import GOLDEN_VERSION, MATRIX, commands, is_done


def record(config_id: str, recall: float, date: str = "2026-10-20", version: str = "v1") -> dict:
    """A made-up retrieval result in the shape run_retrieval_eval.py saves."""
    summary = {"n": 4, "recall@1": recall, "recall@3": recall, "recall@5": recall,
               "strict_recall@5": recall, "mrr": recall, "ndcg@5": recall}  # fmt: skip
    return {
        "config_id": config_id,
        "split": "dev",
        "date": date,
        "git_commit": "abc1234",
        "settings": {
            "golden_version": version,
            "chunk_strategy": "fixed",
            "chunk_size": 200,
            "chunk_overlap": 0,
            "chunk_unit": "tokens",
            "cleaned": True,
            "includes": False,
            "chunk_count": 10,
        },  # fmt: skip
        "overall": summary,
        "per_type": {"factual": summary},
        "per_domain": {"docs": summary},
        "search_latency_ms": {"n": 4, "p50": 2.0, "p95": 3.0},
    }


def test_latest_per_config_keeps_newest_and_drops_other_exams():
    records = [
        record("C1", 0.5, date="2026-10-19"),
        record("C1", 0.75, date="2026-10-20"),
        record("C0", 0.25),
        record("C9", 1.0, version="v0"),  # another golden version: never in the table
    ]
    rows = latest_per_config(records, "v1", "dev")
    assert [r["config_id"] for r in rows] == ["C0", "C1"]
    assert rows[1]["overall"]["recall@5"] == 0.75


def test_main_table_bolds_the_best_and_says_na_for_missing_fields():
    lines = main_table([record("C0", 0.25), record("C1", 0.75)])
    assert len(lines) == 4  # header, separator, two rows
    assert "**0.750**" in lines[3] and "**" not in lines[2].split("| 10 |")[1].split("|")[2]
    assert "| n/a |" in lines[2]  # no ingest_seconds in an old manifest


def test_per_domain_table_shows_na_for_a_missing_domain():
    lines = per_domain_table([record("C0", 0.5)])
    assert "0.500 / 0.500" in lines[2] and "n/a" in lines[2]


def test_replace_block_keeps_the_hand_written_text():
    text = f"intro\n{START}\nold\n{END}\nnotes\n"
    assert replace_block(text, "new") == f"intro\n{START}\nnew\n{END}\nnotes\n"
    with pytest.raises(ValueError):
        replace_block("no markers here", "new")


def test_matrix_ids_and_collections_are_unique():
    ids = [config_id for config_id, _, _ in MATRIX]
    collections = [collection for _, collection, _ in MATRIX]
    assert len(set(ids)) == len(ids) and len(set(collections)) == len(collections)


def test_commands_ingest_then_score_the_same_collection():
    ingest, evaluate = commands("C1-400-v1", "demo", ["--strategy", "recursive"])
    assert ingest[-2:] == ["--collection", "demo"]
    assert evaluate[evaluate.index("--collection") + 1] == "demo"
    assert "--ablation" in evaluate and "dev" in evaluate


def test_is_done_needs_same_commit_and_golden_version(tmp_path):
    result = {"git_commit": "abc1234", "settings": {"golden_version": GOLDEN_VERSION}}
    path = tmp_path / "2026-10-20_C1-400-v1_dev_retrieval.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    assert is_done("C1-400-v1", "abc1234", tmp_path)
    assert not is_done("C1-400-v1", "fff0000", tmp_path)  # code changed since
    assert not is_done("C4-200-v1", "abc1234", tmp_path)  # never run

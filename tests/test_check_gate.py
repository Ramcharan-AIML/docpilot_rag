"""Tests for the CI eval gate: the judge (evals/check_gate.py) and its exam (ci.jsonl)."""

from pathlib import Path

from docpilot import config
from evals.check_gate import DEFAULT_TOLERANCE, compare, new_baseline
from evals.common import load_golden_file

BASELINE = {"metrics": {"recall@5": 1.0, "mrr": 0.87}, "tolerance": DEFAULT_TOLERANCE}
FIXTURE_DOCS = Path(__file__).resolve().parent / "fixtures" / "corpus"
CI_GOLDEN = Path(__file__).resolve().parent.parent / "evals" / "golden" / "ci.jsonl"


def test_small_wobble_passes_real_break_fails():
    wobble = compare({"recall@5": 1.0, "mrr": 0.84}, BASELINE)  # one answer: rank 1 -> 2
    assert all(row["passed"] for row in wobble)
    units_bug = compare({"recall@5": 0.778, "mrr": 0.495}, BASELINE)  # measured 2026-10-20
    assert not any(row["passed"] for row in units_bug)


def test_floor_is_baseline_minus_tolerance():
    rows = {row["metric"]: row for row in compare({"recall@5": 1.0, "mrr": 0.9}, BASELINE)}
    assert rows["mrr"]["floor"] == 0.82 and rows["recall@5"]["floor"] == 0.94


def test_new_baseline_keeps_tolerance_and_records_why():
    record = {
        "overall": {"n": 18, "recall@5": 1.0, "mrr": 0.9},
        "git_commit": "abc1234",
        "date": "2026-10-20",
        "settings": {"chunk_strategy": "fixed_tokens", "chunk_size": 200},
    }
    old = {**BASELINE, "tolerance": {"recall@5": 0.1, "mrr": 0.1}, "why_tolerance": "test"}
    baseline = new_baseline(record, old, "an improvement was kept")
    assert baseline["metrics"] == {"recall@5": 1.0, "mrr": 0.9}
    assert baseline["tolerance"] == {"recall@5": 0.1, "mrr": 0.1}
    assert baseline["reason"] == "an improvement was kept"


def test_ci_questions_are_valid_against_the_fixture_corpus(monkeypatch):
    # Every snippet must really be in its fixture page, or the gate measures nothing.
    monkeypatch.setattr(config, "DOCS_DIR", FIXTURE_DOCS)
    items = load_golden_file(CI_GOLDEN)
    assert len([item for item in items if item["should_answer"]]) >= 15

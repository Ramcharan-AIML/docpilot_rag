"""Tests for evals/validate_golden.py: a checker must catch the mistakes it exists for."""

import json

from evals.validate_golden import validate as validate_golden


def validate(golden_dir, docs_dir, min_per_domain=0):
    """Tiny made-up sets cannot have 10 items per domain; that rule has its own test."""
    return validate_golden(golden_dir, docs_dir, min_per_domain)


DOC_TEXT = "Set the default to `None` to make it optional.\nAnother line.\n"


def make_item(item_id="q-001", split="dev", **changes):
    """One valid item; keyword arguments overwrite fields to break it on purpose."""
    item = {
        "id": item_id,
        "question": "How do I make it optional?",
        "type": "how-to",
        "should_answer": True,
        "reference_answer": "Default None.",
        "evidence": [{"doc": "demo/page.md", "snippet": "Set the default to `None`"}],
        "difficulty": "easy",
        "split": split,
        "domain": "docs",
        "notes": "",
    }
    item.update(changes)
    return item


def write_golden(tmp_path, dev_items, test_items=()):
    """Write a fake golden folder and a fake docs folder; return both paths."""
    golden_dir, docs_dir = tmp_path / "golden", tmp_path / "docs"
    golden_dir.mkdir()
    (docs_dir / "demo").mkdir(parents=True)
    (docs_dir / "demo" / "page.md").write_text(DOC_TEXT, encoding="utf-8")
    for split, items in (("dev", dev_items), ("test", test_items)):
        lines = [json.dumps(item) for item in items]
        (golden_dir / f"{split}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return golden_dir, docs_dir


def test_valid_file_has_no_errors(tmp_path):
    golden_dir, docs_dir = write_golden(tmp_path, [make_item()], [make_item("q-002", "test")])
    items, errors = validate(golden_dir, docs_dir)
    assert errors == []
    assert len(items) == 2


def test_snippet_typo_is_caught(tmp_path):
    # One wrong character ("Non" instead of "None") must fail: this is the main job.
    bad = make_item(evidence=[{"doc": "demo/page.md", "snippet": "Set the default to `Non`"}])
    _, errors = validate(*write_golden(tmp_path, [bad]))
    assert any("snippet not in" in error for error in errors)


def test_duplicate_id_across_files_is_caught(tmp_path):
    _, errors = validate(*write_golden(tmp_path, [make_item()], [make_item(split="test")]))
    assert any("duplicate id q-001" in error for error in errors)


def test_missing_field_is_caught(tmp_path):
    item = make_item()
    del item["evidence"]
    _, errors = validate(*write_golden(tmp_path, [item]))
    assert any("missing fields ['evidence']" in error for error in errors)


def test_unanswerable_with_evidence_is_caught(tmp_path):
    bad = make_item(type="not-in-docs", should_answer=False)  # still has evidence
    _, errors = validate(*write_golden(tmp_path, [bad]))
    assert any("should_answer is false but evidence is not empty" in error for error in errors)


def test_item_in_wrong_split_file_is_caught(tmp_path):
    _, errors = validate(*write_golden(tmp_path, [make_item(split="test")]))
    assert any("split is 'test'" in error for error in errors)


def test_broken_json_line_is_reported_not_crashing(tmp_path):
    golden_dir, docs_dir = write_golden(tmp_path, [make_item()])
    with (golden_dir / "dev.jsonl").open("a", encoding="utf-8") as file:
        file.write("{not json\n")
    _, errors = validate(golden_dir, docs_dir)
    assert any("not valid JSON" in error for error in errors)


def test_domain_must_match_the_register_entry_of_its_document(tmp_path):
    # "fastapi" is a docs source in ingestion/sources.py, so domain "learning" is wrong.
    bad = make_item(domain="learning", evidence=[{"doc": "fastapi/page.md", "snippet": "Another"}])
    golden_dir, docs_dir = write_golden(tmp_path, [bad])
    (docs_dir / "fastapi").mkdir()
    (docs_dir / "fastapi" / "page.md").write_text(DOC_TEXT, encoding="utf-8")
    _, errors = validate(golden_dir, docs_dir)
    assert any("but fastapi/page.md is 'docs'" in error for error in errors)


def test_too_few_items_in_a_domain_is_caught(tmp_path):
    golden_dir, docs_dir = write_golden(tmp_path, [make_item()])
    _, errors = validate_golden(golden_dir, docs_dir)  # the real rule: 10 per domain
    assert any("domain 'learning' has 0 items; needs at least 10" in error for error in errors)

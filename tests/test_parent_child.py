"""Tests for chunkers/parent_child.py (C3): children point to parents; hits lift to parents."""

from docpilot.ingestion.chunkers.parent_child import (
    lift_to_parents,
    load_parents,
    parent_child_chunks,
    save_parents,
)

DOC = (
    "# Body\n\n## Models\n\n"
    + " ".join(f"Sentence number {i} explains models." for i in range(30))
    + "\n\n## Results\n\nThe function receives the model.\n"
)


def test_every_child_lies_inside_its_parent():
    parents: dict[str, dict] = {}
    children = parent_child_chunks(DOC, "a.md", 32, 0, parent_tokens=800, parents=parents)
    assert len(children) > len(parents) >= 2  # several small children per section
    for child in children:
        parent = parents[child.parent_id]
        assert child.text in parent["text"]
        assert child.strategy == "parent_child"


def test_parents_save_and_load(tmp_path):
    parents = {"a.md#p0": {"source": "a.md", "text": "hello", "char_start": 0}}
    save_parents(parents, tmp_path / "parents.json")
    assert load_parents(tmp_path / "parents.json") == parents


def test_lift_keeps_best_first_and_each_parent_once():
    parents = {
        "a#p0": {"text": "parent zero"},
        "a#p1": {"text": "parent one"},
    }
    hits = [
        {"parent_id": "a#p1", "text": "child 1a", "score": 0.9},
        {"parent_id": "a#p1", "text": "child 1b", "score": 0.8},
        {"parent_id": "a#p0", "text": "child 0a", "score": 0.7},
    ]
    lifted = lift_to_parents(hits, parents, limit=10)
    assert [hit["text"] for hit in lifted] == ["parent one", "parent zero"]
    assert lifted[0]["child_text"] == "child 1a"
    assert lifted[0]["score"] == 0.9
    assert len(lift_to_parents(hits, parents, limit=1)) == 1

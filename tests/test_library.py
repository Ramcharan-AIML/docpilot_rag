"""Tests for the library panel data (D-066): built only from what the collection holds."""

from docpilot.library import describe, pretty_name


def test_pretty_names() -> None:
    assert pretty_name("fastapi/query-params.md") == "Query params"
    assert pretty_name("wikipedia/Word_embedding.md") == "Word embedding"


def test_describe_lists_only_sources_in_the_collection_in_register_order() -> None:
    counts = {
        "docker/volumes.md": 10,
        "fastapi/query-params.md": 20,
        "fastapi/path-params.md": 5,
    }
    entries = describe(counts)
    assert [entry["key"] for entry in entries] == ["fastapi", "docker"]  # register order
    fastapi = entries[0]
    assert fastapi["title"] == "FastAPI" and fastapi["kind"] == "Official docs"
    assert fastapi["documents"] == ["Path params", "Query params"]
    assert fastapi["chunks"] == 25 and fastapi["licence"] == "MIT"
    assert "interview" not in [entry["key"] for entry in entries]  # not in the collection

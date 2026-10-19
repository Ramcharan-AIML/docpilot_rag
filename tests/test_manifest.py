"""Tests for ingestion/manifest.py: the label that says how a collection was built."""

from docpilot.ingestion.manifest import load_manifest, save_manifest


def test_saved_manifest_reads_back_the_same(tmp_path):
    settings = {"chunk_strategy": "fixed_tokens", "chunk_size": 400, "cleaned": True}
    save_manifest("docs_x", settings, folder=tmp_path)
    assert load_manifest("docs_x", folder=tmp_path) == settings


def test_reingest_overwrites_the_old_label(tmp_path):
    save_manifest("docs_x", {"chunk_size": 800}, folder=tmp_path)
    save_manifest("docs_x", {"chunk_size": 400}, folder=tmp_path)
    assert load_manifest("docs_x", folder=tmp_path) == {"chunk_size": 400}


def test_collection_without_manifest_gives_none(tmp_path):
    # Collections built before step 2.6 have no label; the eval then falls back to config.
    assert load_manifest("docpilot_naive", folder=tmp_path) is None

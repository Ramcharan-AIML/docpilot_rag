"""Tests for ingestion/includes.py: markers become real code; missing files stay visible."""

from docpilot.ingestion.includes import find_include_paths, marker_path, resolve_includes

PAGE = (
    "The simplest file:\n\n"
    "{* ../../docs_src/first/app.py *}\n\n"
    "Highlighted:\n\n"
    "{* ../../docs_src/first/app.py hl[1] *}\n"
)


def make_code_root(tmp_path):
    code = tmp_path / "docs_src" / "first"
    code.mkdir(parents=True)
    (code / "app.py").write_text("from fastapi import FastAPI\n\napp = FastAPI()\n", "utf-8")
    return tmp_path


def test_marker_path_drops_the_relative_prefix():
    assert marker_path("../../docs_src/a/b.py") == "docs_src/a/b.py"


def test_find_include_paths_lists_each_file_once():
    assert find_include_paths(PAGE) == ["docs_src/first/app.py"]


def test_markers_become_python_code_blocks(tmp_path):
    text, resolved, missing = resolve_includes(PAGE, make_code_root(tmp_path))
    assert resolved == 2 and missing == []
    assert "{*" not in text
    assert "```python\nfrom fastapi import FastAPI\n\napp = FastAPI()\n```" in text
    assert text.startswith("The simplest file:")  # the prose around it is unchanged


def test_missing_file_is_reported_and_marker_kept(tmp_path):
    page = "{* ../../docs_src/nowhere.py *}\n"
    text, resolved, missing = resolve_includes(page, tmp_path)
    assert resolved == 0
    assert missing == ["docs_src/nowhere.py"]
    assert text == page  # still visible, so the failure shows up in the chunks too


def test_text_without_markers_is_unchanged(tmp_path):
    text = "No markers here, only `{code}` and *stars*.\n"
    assert resolve_includes(text, tmp_path) == (text, 0, [])


def test_source_without_code_folder_is_left_alone_fix_a(tmp_path):
    # The Word notes quote a marker as an example: no code folder, so nothing is "missing".
    notes = 'They write "{* ../../docs_src/x.py *}" instead of code.\n'
    assert resolve_includes(notes, tmp_path / "interview") == (notes, 0, [])

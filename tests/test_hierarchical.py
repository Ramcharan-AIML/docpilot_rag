"""Tests for chunkers/hierarchical.py (C4): sections, whole code blocks, heading prefix."""

from docpilot.ingestion.chunkers.hierarchical import hierarchical_chunks
from docpilot.ingestion.chunkers.tokens import count_tokens

CODE = "```python\n" + "\n\n".join(f"value_{i} = compute({i})" for i in range(12)) + "\n```"
DOC = (
    "# Query Parameters\n\n## Defaults\n\nA default makes a parameter optional.\n\n"
    f"{CODE}\n\nMore text after the code.\n\n## Required\n\nNo default means required.\n"
)


def test_code_block_is_never_split_even_when_bigger_than_the_size():
    assert count_tokens(CODE) > 40  # bigger than the chunk size below
    chunks = hierarchical_chunks(DOC, "a.md", chunk_tokens=40)
    assert sum(CODE in chunk.text for chunk in chunks) == 1  # whole, in exactly one chunk


def test_a_heading_always_starts_a_new_chunk():
    chunks = hierarchical_chunks(DOC, "a.md", chunk_tokens=400)
    assert not any("Defaults" in c.text and "## Required" in c.text for c in chunks)
    # "# Query Parameters" directly followed by "## Defaults": kept together, not alone
    assert chunks[0].text.startswith("# Query Parameters\n\n## Defaults")


def test_prefix_is_the_heading_path_and_text_stays_an_exact_slice():
    chunks = hierarchical_chunks(DOC, "a.md", chunk_tokens=400)
    last = chunks[-1]
    assert last.prefix == "Query Parameters > Required\n\n"
    assert DOC[last.char_start : last.char_start + len(last.text)] == last.text


def test_with_and_without_prefix_make_the_same_chunks():
    with_prefix = hierarchical_chunks(DOC, "a.md", chunk_tokens=40)
    without = hierarchical_chunks(DOC, "a.md", chunk_tokens=40, with_prefix=False)
    assert [c.text for c in with_prefix] == [c.text for c in without]
    assert all(c.prefix == "" for c in without)
    assert without[0].strategy == "hierarchical_noprefix"

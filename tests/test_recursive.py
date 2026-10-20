"""Tests for chunkers/recursive.py (C1). Small sizes keep the made-up texts short."""

from docpilot.ingestion.chunkers.recursive import recursive_chunks, split_span
from docpilot.ingestion.chunkers.tokens import count_tokens

SECTION_A = "## Alpha\n\nCats sleep most of the day. They like warm places."
SECTION_B = "## Beta\n\nPython is a programming language. It reads like English."
DOC = f"# Title\n\n{SECTION_A}\n\n{SECTION_B}\n"


def test_short_text_is_one_trimmed_chunk():
    [chunk] = recursive_chunks("  hello world \n", "a.md", chunk_tokens=50, overlap_tokens=0)
    assert chunk.text == "hello world"
    assert chunk.char_start == 2
    assert chunk.strategy == "recursive"


def test_heading_break_is_used_before_smaller_ones():
    # Each section fits in 20 tokens, both together do not: the cut is at "## Beta".
    chunks = recursive_chunks(DOC, "a.md", chunk_tokens=20, overlap_tokens=0)
    assert any(chunk.text.startswith("## Beta") for chunk in chunks)
    assert not any("Alpha" in chunk.text and "Beta" in chunk.text for chunk in chunks)


def test_chunks_fit_are_exact_slices_and_lose_nothing():
    text = DOC * 5
    chunks = recursive_chunks(text, "a.md", chunk_tokens=30, overlap_tokens=5)
    covered = set()
    for chunk in chunks:
        assert count_tokens(chunk.text) <= 30
        assert text[chunk.char_start : chunk.char_start + len(chunk.text)] == chunk.text
        covered.update(range(chunk.char_start, chunk.char_start + len(chunk.text)))
    assert all(i in covered for i, char in enumerate(text) if not char.isspace())


def test_text_without_any_separator_is_hard_cut():
    # No spaces, full stops or line breaks. Not "x" * 3000: the tokenizer turns any word
    # over 100 characters into ONE [UNK] token, so that text would "fit" in 1 token.
    text = "a," * 1000
    chunks = recursive_chunks(text, "a.md", chunk_tokens=50, overlap_tokens=0)
    assert len(chunks) > 1
    assert "".join(chunk.text for chunk in chunks) == text


def test_split_span_keeps_the_heading_with_its_section():
    text = "intro\n## Next\nbody"
    pieces = split_span(text, (0, len(text)), "\n## ")
    assert [text[a:b] for a, b in pieces] == ["intro\n", "## Next\nbody"]

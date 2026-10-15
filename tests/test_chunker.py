"""Tests for chunker.py. Small sizes (10/3) keep the made-up texts short and readable."""

import string
from itertools import pairwise

import pytest

from docpilot.chunker import fixed_size_chunks

# 26 letters + 10 digits = 36 different characters, so every position is easy to spot
SAMPLE = string.ascii_lowercase + string.digits


def test_empty_text_gives_no_chunks() -> None:
    assert fixed_size_chunks("", "a.md", chunk_size=10, overlap=3) == []


def test_short_text_gives_one_chunk() -> None:
    chunks = fixed_size_chunks("hello", "a.md", chunk_size=10, overlap=3)

    assert len(chunks) == 1
    assert chunks[0].text == "hello"
    assert chunks[0].source == "a.md"


def test_neighbours_share_the_overlap() -> None:
    chunks = fixed_size_chunks(SAMPLE, "a.md", chunk_size=10, overlap=3)

    for left, right in pairwise(chunks):  # (0,1), (1,2), (2,3) ...
        assert left.text[-3:] == right.text[:3]


def test_chunk_numbers_have_no_gaps() -> None:
    chunks = fixed_size_chunks(SAMPLE, "a.md", chunk_size=10, overlap=3)

    assert [c.chunk_number for c in chunks] == list(range(len(chunks)))


def test_no_text_is_lost() -> None:
    # Glue chunk 0 to every later chunk minus its repeated start: we must get the input back.
    chunks = fixed_size_chunks(SAMPLE, "a.md", chunk_size=10, overlap=3)

    rebuilt = chunks[0].text + "".join(c.text[3:] for c in chunks[1:])
    assert rebuilt == SAMPLE


@pytest.mark.parametrize(("chunk_size", "overlap"), [(10, 10), (10, 15), (10, -1), (0, 0)])
def test_bad_settings_raise(chunk_size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        fixed_size_chunks(SAMPLE, "a.md", chunk_size=chunk_size, overlap=overlap)

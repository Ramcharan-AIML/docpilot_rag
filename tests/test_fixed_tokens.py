"""Tests for fixed_token_chunks (loads the pinned model's tokenizer, like test_tokens)."""

from itertools import pairwise

import pytest

from docpilot.ingestion.chunkers.fixed import fixed_token_chunks
from docpilot.ingestion.chunkers.tokens import MAX_CHUNK_TOKENS, count_tokens

# 30 different words that are each one token, so token positions are easy to reason about
WORDS = " ".join(
    "one two three four five six seven eight nine ten red blue green black white "
    "cat dog cow pig hen sun moon star tree leaf rain snow wind fire stone".split()
)


def test_empty_text_gives_no_chunks():
    assert fixed_token_chunks("", "a.md", chunk_tokens=10, overlap_tokens=3) == []


def test_every_chunk_has_at_most_n_tokens():
    chunks = fixed_token_chunks(WORDS, "a.md", chunk_tokens=10, overlap_tokens=3)
    assert len(chunks) == 4  # starts at tokens 0, 7, 14, 21; the last one reaches token 29
    assert all(count_tokens(chunk.text) <= 10 for chunk in chunks)
    assert [chunk.chunk_number for chunk in chunks] == [0, 1, 2, 3]


def test_neighbours_share_the_overlap_tokens():
    chunks = fixed_token_chunks(WORDS, "a.md", chunk_tokens=10, overlap_tokens=3)
    for left, right in pairwise(chunks):
        assert left.text.split()[-3:] == right.text.split()[:3]


def test_text_is_sliced_exactly_from_the_document():
    # Indentation and line breaks inside code must survive (tokens alone would lose them).
    code = "def read_item(item_id: int):\n    return {'item_id': item_id}\n"
    [chunk] = fixed_token_chunks(code, "a.md", chunk_tokens=100, overlap_tokens=10)
    assert chunk.text == code.rstrip("\n")
    assert code[chunk.char_start :].startswith(chunk.text)
    assert chunk.strategy == "fixed_tokens"


def test_sizes_over_the_model_limit_are_refused():
    with pytest.raises(ValueError, match="at most"):
        fixed_token_chunks(WORDS, "a.md", chunk_tokens=MAX_CHUNK_TOKENS + 1, overlap_tokens=0)

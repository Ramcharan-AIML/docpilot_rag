"""Tests for ingestion/chunkers/tokens.py (loads the pinned model, like test_embedder)."""

from docpilot.embedding.dense import get_model
from docpilot.ingestion.chunkers.tokens import (
    MAX_CHUNK_TOKENS,
    MODEL_MAX_TOKENS,
    count_tokens,
    fits_in_model,
)


def test_limit_matches_the_loaded_model():
    # If someone changes the model or revision, this fails instead of truncating silently.
    assert get_model().max_seq_length == MODEL_MAX_TOKENS
    assert MAX_CHUNK_TOKENS == MODEL_MAX_TOKENS - 2


def test_special_tokens_are_not_counted():
    # "hello world" is 2 words the tokenizer knows; [CLS] and [SEP] are left out.
    assert count_tokens("hello world") == 2
    assert count_tokens("") == 0


def test_code_uses_more_tokens_than_characters_suggest():
    # Identifiers split into pieces: one "word" of code can be many tokens.
    assert count_tokens("model_name.value") > 2


def test_fits_in_model_at_the_border():
    # "hello" is one token, so N repeats is N tokens (the space is not a token).
    assert fits_in_model("hello " * MAX_CHUNK_TOKENS)
    assert not fits_in_model("hello " * (MAX_CHUNK_TOKENS + 1))

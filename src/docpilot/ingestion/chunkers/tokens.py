"""Measure text in the embedding model's tokens (step 2.6), the unit every chunker uses.

Why tokens, not characters: the model reads tokens and silently ignores everything after
its limit. Verified 2026-10-17 on the pinned revision: max_seq_length 512, and the
tokenizer adds 2 special tokens ([CLS] at the start, [SEP] at the end) to every text.
Characters are only a rough guess: our 4 pages average about 3.2 characters per token,
code and identifiers fewer.
"""

from docpilot.embedding.dense import get_model

MODEL_MAX_TOKENS = 512  # bge-small-en-v1.5 (D-038)
SPECIAL_TOKENS = 2  # [CLS] + [SEP]
# The most text tokens one chunk can have before the model starts cutting it off.
MAX_CHUNK_TOKENS = MODEL_MAX_TOKENS - SPECIAL_TOKENS  # 510


def count_tokens(text: str) -> int:
    """How many tokens the model reads for `text`, not counting [CLS] and [SEP].

    Same tokenizer as the embedder (taken from the loaded model), so the count can never
    drift from what is really embedded. verbose=False hides the "longer than 512" warning:
    measuring long texts is exactly what we want here.
    """
    return len(get_model().tokenizer.encode(text, add_special_tokens=False, verbose=False))


def token_offsets(text: str) -> list[tuple[int, int]]:
    """(start, end) character positions of every token of `text`, in order.

    Lets a chunker cut at a token border and still slice the ORIGINAL text, so spaces,
    line breaks and code indentation survive (the tokens themselves are lower-cased).
    """
    encoding = get_model().tokenizer(
        text, add_special_tokens=False, return_offsets_mapping=True, verbose=False
    )
    return encoding["offset_mapping"]


def fits_in_model(text: str) -> bool:
    """True if the model will see all of `text` (nothing silently cut off)."""
    return count_tokens(text) <= MAX_CHUNK_TOKENS

"""Tests for chunkers/semantic.py (C2). Uses the real embedding model (like test_embedder)."""

from docpilot.ingestion.chunkers.semantic import percentile, semantic_chunks, sentence_spans

CATS = "Cats are small furry pets. Cats sleep most of the day. A cat purrs when it is happy."
CODE = "```python\nprint('hello')\n\nx = 1\n```"
PYTHON = "Python lists store items in order. A Python dict maps keys to values."


def test_sentences_end_at_a_full_stop_followed_by_space():
    text = "Use model_name.value here. Then read the docs."
    spans = sentence_spans(text, (0, len(text)))
    assert [text[a:b] for a, b in spans] == ["Use model_name.value here.", "Then read the docs."]


def test_percentile_is_nearest_rank():
    assert percentile([5, 1, 3, 2, 4], 20) == 1
    assert percentile([5, 1, 3, 2, 4], 100) == 5


def test_topic_jump_starts_a_new_chunk_and_code_stays_whole():
    text = f"{CATS}\n\n{CODE}\n\n{PYTHON}\n"
    # percentile 20 of 6 similarities -> one cut, at the biggest topic jump
    chunks = semantic_chunks(text, "a.md", chunk_tokens=400, percentile_cut=20)
    assert len(chunks) == 2
    assert sum(CODE in chunk.text for chunk in chunks) == 1
    assert "Cats" in chunks[0].text and "Cats" not in chunks[1].text
    assert all(text[c.char_start : c.char_start + len(c.text)] == c.text for c in chunks)

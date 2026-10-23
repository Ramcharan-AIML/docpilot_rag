"""Tests for the output guard: cite or refuse, prompt leak, secrets."""

import pytest

from docpilot import config
from docpilot.guardrails.output_guard import CANARY, check_output, cited_numbers


@pytest.mark.parametrize(
    ("answer", "numbers"),
    [
        ("Use Query(default=None) [1].", [1]),
        ("Both work [1, 3].", [1, 3]),
        ("See [1][2].", [1, 2]),
        ("Use Query【1】 and Path【4】.", [1, 4]),  # full-width brackets, seen from gpt-oss
        ("Open /docs【1†L1-L4】.", [1]),  # with a line range, also seen
        ("No citation here.", []),
    ],
)
def test_every_citation_style_is_found(answer: str, numbers: list[int]) -> None:
    assert cited_numbers(answer) == numbers


def test_code_is_not_read_as_a_citation() -> None:
    answer = "Take the first item with `items[0]` [2].\n```python\nx = row[5]\n```"
    assert cited_numbers(answer) == [2]


def test_cited_answer_passes_unchanged() -> None:
    result = check_output("Make it optional with Query(default=None) [1].", n_sources=4)
    assert result.allowed
    assert result.text == "Make it optional with Query(default=None) [1]."


def test_answer_without_citation_becomes_not_found() -> None:
    result = check_output("Here is a poem about love, roses are red...", n_sources=4)
    assert not result.allowed
    assert result.reason == "no_citation"
    assert result.text == config.NOT_FOUND_PHRASE


def test_citation_to_a_chunk_we_never_sent_is_rejected() -> None:
    result = check_output("This is true [7].", n_sources=4)
    assert result.reason == "bad_citation"
    assert result.text == config.NOT_FOUND_PHRASE


def test_not_found_answer_is_normalised_to_the_exact_sentence() -> None:
    answer = f"Sorry. {config.NOT_FOUND_PHRASE} Maybe check the docs."
    result = check_output(answer, n_sources=4)
    assert result.allowed
    assert result.reason == "not_found"
    assert result.text == config.NOT_FOUND_PHRASE


def test_canary_in_answer_is_blocked_as_prompt_leak() -> None:
    result = check_output(f"My rules say: marker {CANARY} [1]", n_sources=4)
    assert not result.allowed
    assert result.reason == "prompt_leak"
    assert result.text == config.BLOCKED_PHRASE
    assert CANARY not in result.text


def test_key_shaped_strings_are_redacted() -> None:
    fake_key = "gsk_" + "A1b2C3d4E5f6G7h8I9j0K1l2"  # made up, not a real key
    result = check_output(f"Set GROQ_API_KEY={fake_key} in .env [1].", n_sources=4)
    assert result.allowed
    assert result.reason == "redacted_secret"
    assert fake_key not in result.text
    assert "[REDACTED]" in result.text

"""Tests for chunkers/contextual.py with a fake LLM: no API calls, no key needed."""

import httpx
from openai import RateLimitError

from docpilot.ingestion.chunkers.base import Chunk
from docpilot.ingestion.chunkers.contextual import ContextWriter, section_around

DOC = "# Guide\n\nIntro.\n\n## Install\n\nRun pip.\n\n## Usage\n\nCall the function.\n"


def fake_llm(calls: list[str]):
    def ask(system: str, user: str) -> str:
        calls.append(user)
        return "  This chunk is\nabout usage.  "

    return ask


def usage_chunk() -> Chunk:
    start = DOC.index("Call the function.")
    return Chunk(text="Call the function.", source="g.md", chunk_number=0, char_start=start)


def test_section_is_the_level_two_section_around_the_chunk():
    start = DOC.index("Call")
    title, section = section_around(DOC, start, start + 4)
    assert title == "Guide"
    assert section.startswith("## Usage") and "pip" not in section


def test_note_goes_into_prefix_and_text_is_unchanged(tmp_path):
    calls: list[str] = []
    writer = ContextWriter(fake_llm(calls), cache_path=tmp_path / "cache.jsonl", model="m")
    [chunk] = writer.add_context([usage_chunk()], DOC)
    assert chunk.prefix == "This chunk is about usage.\n\n"  # squashed to one line
    assert chunk.text == "Call the function."
    assert chunk.strategy.startswith("contextual+")
    assert len(calls) == 1 and "## Usage" in calls[0]


def test_second_run_uses_the_cache_and_makes_no_calls(tmp_path):
    cache = tmp_path / "cache.jsonl"
    ContextWriter(fake_llm([]), cache_path=cache, model="m").add_context([usage_chunk()], DOC)
    calls: list[str] = []
    writer = ContextWriter(fake_llm(calls), cache_path=cache, model="m")
    writer.add_context([usage_chunk()], DOC)
    assert calls == []
    assert writer.stats["cache_hits"] == 1 and writer.stats["llm_calls"] == 0


def test_rate_limit_is_retried_and_counted(tmp_path):
    attempts: list[int] = []

    def flaky(system: str, user: str) -> str:
        attempts.append(1)
        if len(attempts) == 1:
            request = httpx.Request("POST", "https://example.invalid")
            response = httpx.Response(429, headers={"retry-after": "0"}, request=request)
            raise RateLimitError("slow down", response=response, body=None)
        return "Note."

    writer = ContextWriter(flaky, cache_path=tmp_path / "cache.jsonl", model="m")
    writer.add_context([usage_chunk()], DOC)
    assert writer.stats["retries_429"] == 1 and writer.stats["llm_calls"] == 1

"""Contextual chunking (C5): an LLM writes a short "sticky note" for every chunk.

The note ("This chunk is from Query Parameters and explains default values.") goes into
`prefix`, so it is embedded with the chunk; `text` stays the exact slice (the plan's
display_text). Base chunks come from another strategy (default hierarchical).

Cost control (plan 2.6.2, D-041):
- the prompt holds the chunk's SECTION (level-1/2 heading to the next one), not the whole
  page: Groq's free tier allows 8000 tokens per minute (checked 2026-10-19), and a whole
  page with code is about 4000 tokens, so whole-page prompts would allow 2 calls a minute;
- every note is cached in data/processed/context_cache.jsonl; a re-run costs zero calls;
- 429 answers are retried after the server's retry-after, and counted;
- calls, cache hits, retries and minutes are returned as stats for the manifest.
"""

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path

from openai import RateLimitError

from docpilot import config
from docpilot.ingestion.blocks import parse_blocks
from docpilot.ingestion.chunkers.base import Chunk
from docpilot.ingestion.chunkers.tokens import count_tokens

SYSTEM = (
    "You write short context notes that help a search engine find text. Reply with the note only."
)
PROMPT = """<section title="{title}">
{section}
</section>

Here is a chunk from this section:
<chunk>
{chunk}
</chunk>

Write 1-2 short sentences (at most 50 words) that situate this chunk within the document,
to improve search retrieval of the chunk. Reply with the sentences only."""
SECTION_MAX_TOKENS = 1500  # longer sections are shortened to a window around the chunk
WINDOW_CHARS = 2500  # characters kept on each side of the chunk in that case


def section_around(text: str, start: int, end: int) -> tuple[str, str]:
    """(page title, the level-1/2 section that holds text[start:end])."""
    blocks = parse_blocks(text)
    title = next((b.text for b in blocks if b.kind == "heading"), "")
    section_start, section_end = 0, len(text)
    for block in blocks:
        if block.kind == "heading" and len(block.heading_path) <= 2:
            if block.start <= start:
                section_start = block.start
            elif block.start >= end:
                section_end = block.start
                break
    section = text[section_start:section_end]
    if count_tokens(section) > SECTION_MAX_TOKENS:
        section = text[
            max(section_start, start - WINDOW_CHARS) : min(section_end, end + WINDOW_CHARS)
        ]
    return title, section


def groq_chat() -> Callable[[str, str], str]:
    """Default LLM: the project's client, with 429 retries counted by ContextWriter."""
    from docpilot.llm.client import chat, get_llm_client  # only when really needed

    client = get_llm_client().with_options(max_retries=0)
    return lambda system, user: chat(client, system, user)


class ContextWriter:
    """Writes (or reads from cache) one context note per chunk and keeps the cost stats."""

    def __init__(
        self,
        ask_llm: Callable[[str, str], str] | None = None,
        cache_path: Path = config.CONTEXT_CACHE,
        model: str = config.LLM_MODEL,
        max_attempts: int = 6,
    ) -> None:
        self.ask_llm = ask_llm  # created on the first uncached chunk (tests pass a fake)
        self.cache_path = cache_path
        self.model = model
        self.max_attempts = max_attempts
        self.cache: dict[str, str] = {}
        if cache_path.exists():
            for line in cache_path.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                self.cache[row["key"]] = row["context"]
        self.stats = {"llm_calls": 0, "cache_hits": 0, "retries_429": 0, "llm_seconds": 0.0}

    def key(self, source: str, chunk_text: str) -> str:
        raw = f"{config.CONTEXT_PROMPT_VERSION}|{self.model}|{source}|{chunk_text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def note(self, text: str, chunk: Chunk) -> str:
        key = self.key(chunk.source, chunk.text)
        if key in self.cache:
            self.stats["cache_hits"] += 1
            return self.cache[key]
        if self.ask_llm is None:
            self.ask_llm = groq_chat()
        title, section = section_around(text, chunk.char_start, chunk.char_start + len(chunk.text))
        user = PROMPT.format(title=title, section=section, chunk=chunk.text)
        started = time.perf_counter()
        for attempt in range(1, self.max_attempts + 1):
            try:
                context = " ".join(self.ask_llm(SYSTEM, user).split())  # one line
                break
            except RateLimitError as error:
                if attempt == self.max_attempts:
                    raise
                self.stats["retries_429"] += 1
                time.sleep(float(error.response.headers.get("retry-after", 5 * attempt)))
        self.stats["llm_calls"] += 1
        self.stats["llm_seconds"] += time.perf_counter() - started
        self.cache[key] = context
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("a", encoding="utf-8") as cache_file:  # saved at once:
            cache_file.write(json.dumps({"key": key, "context": context}) + "\n")  # crash-safe
        return context

    def add_context(self, chunks: list[Chunk], text: str) -> list[Chunk]:
        """Put each chunk's note in front of its existing prefix (heading path, if any)."""
        for chunk in chunks:
            chunk.prefix = self.note(text, chunk) + "\n\n" + chunk.prefix
            chunk.strategy = f"contextual+{chunk.strategy}"
        return chunks

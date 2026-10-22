"""Cache for query-transform outputs (step 3.6): pay for each LLM call once.

evals/cache/transforms_<name>_<model>_<prompt version>.json maps question -> {"texts": [...],
"llm_ms": ..., "retries_429": ...}. The first eval run calls the LLM; every later run reads
the file, so it is free and gives the same rewrites (repeatable numbers). The file is
committed: anyone can re-run the eval without an API key.
"""

import json
import time
from pathlib import Path

from openai import RateLimitError

from docpilot import config
from docpilot.retrieval.query_transforms import (
    PROMPT_VERSION,
    Ask,
    default_ask,
    model_tag,
    transform,
)

CACHE_DIR = config.PROJECT_ROOT / "evals" / "cache"
MAX_ATTEMPTS = 5


def cache_path(name: str, folder: Path = CACHE_DIR) -> Path:
    return folder / f"transforms_{name}_{model_tag()}_{PROMPT_VERSION}.json"


class TransformCache:
    """get(question) returns the cached rewrite, or calls the LLM once and saves it."""

    def __init__(self, name: str, ask: Ask | None = None, folder: Path = CACHE_DIR) -> None:
        self.name = name
        self.path = cache_path(name, folder)
        self.entries: dict[str, dict] = (
            json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        )
        self._ask = ask  # made on first need: a full cache needs no API key
        self.new_calls = 0

    def get(self, question: str) -> dict:
        if question not in self.entries:
            self.entries[question] = self._call_llm(question)
            self.new_calls += 1
            self.save()  # after every call: a crash or Ctrl+C loses nothing already paid for
        return self.entries[question]

    def _call_llm(self, question: str) -> dict:
        if self._ask is None:
            self._ask = default_ask()
        start = time.perf_counter()
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                texts = transform(self.name, question, self._ask)
                llm_ms = round((time.perf_counter() - start) * 1000, 1)
                return {"texts": texts, "llm_ms": llm_ms, "retries_429": attempt - 1}
            except RateLimitError as error:
                if attempt == MAX_ATTEMPTS:
                    raise
                # Free tier: about 30 requests and 8,000 tokens per minute (Groq, 2026-10-22).
                wait = float(error.response.headers.get("retry-after", 10 * attempt))
                print(f"  429 rate limit, waiting {wait:.0f} s (attempt {attempt})")
                time.sleep(wait)
        raise AssertionError("unreachable")

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(self.entries, indent=2, ensure_ascii=False) + "\n"
        self.path.write_text(text, encoding="utf-8")

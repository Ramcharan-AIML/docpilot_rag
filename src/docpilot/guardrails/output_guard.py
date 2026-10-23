"""Output guard (step 6.4): checks the LLM answer BEFORE the user sees it.

Rules, in order:
1. Prompt leak: our canary string appears -> block (the system prompt leaked).
2. Not found: the answer contains the abstention sentence -> return exactly that sentence.
3. Cite or refuse: no citation at all, or a citation to a chunk we never sent -> abstain.
4. Secrets: anything shaped like an API key is redacted, never shown.

No extra LLM call: every check is a string or regex test, so it costs microseconds.
"""

import re

from docpilot import config
from docpilot.guardrails.input_guard import GuardResult

# A random marker placed in the guarded system prompt (rag.py). It means nothing, so no
# normal answer ever contains it: if it shows up, the prompt leaked. Zero false positives.
CANARY = "DP-CANARY-79eee776"

# The LLM cites in more than one style. Seen in our cached answers (2026-10-22, gpt-oss-120b):
# "[2]", "[1, 2]", "【1】" (full-width brackets) and "【1†L1-L4】" (with a line range).
# A guard that only knew "[n]" would wrongly refuse good answers.
CITATION = re.compile(r"[\[【]\s*(\d+(?:\s*,\s*\d+)*)\s*(?:†[^\]】]*)?[\]】]")

# Code is not prose: `items[0]` or a ```python block``` must not count as citation [0].
CODE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)

# Shapes of common API keys. Prefixes as published by each provider (re-check before
# relying on them): Groq "gsk_", OpenAI/OpenRouter "sk-", AWS access key id "AKIA",
# Google "AIza".
SECRET_PATTERNS = [
    re.compile(r"\bgsk_[A-Za-z0-9]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}"),
]
REDACTED = "[REDACTED]"


def cited_numbers(answer: str) -> list[int]:
    """Every chunk number the answer cites, code blocks ignored. "[1, 3]" gives [1, 3]."""
    prose = CODE.sub(" ", answer)
    numbers = []
    for match in CITATION.finditer(prose):
        numbers += [int(part) for part in match.group(1).split(",")]
    return numbers


def redact_secrets(text: str) -> tuple[str, int]:
    """Replace key-shaped strings with [REDACTED]; also return how many were replaced."""
    total = 0
    for pattern in SECRET_PATTERNS:
        text, count = pattern.subn(REDACTED, text)
        total += count
    return text, total


def check_output(answer: str, n_sources: int) -> GuardResult:
    """Allow, fix, or replace one answer. `n_sources` = how many chunks the LLM was given.

    `text` is always what the user should see: the answer itself, the exact not-found
    sentence, or the blocked sentence.
    """
    if CANARY in answer:
        return GuardResult(False, "prompt_leak", config.BLOCKED_PHRASE)

    if config.NOT_FOUND_PHRASE in answer:
        # Consistent abstention: the user (and our evals) see one exact sentence.
        return GuardResult(True, "not_found", config.NOT_FOUND_PHRASE)

    numbers = cited_numbers(answer)
    if not numbers:
        return GuardResult(False, "no_citation", config.NOT_FOUND_PHRASE)
    if any(number < 1 or number > n_sources for number in numbers):
        # A citation to a chunk we never sent is fake evidence.
        return GuardResult(False, "bad_citation", config.NOT_FOUND_PHRASE)

    text, redacted = redact_secrets(answer)
    return GuardResult(True, "redacted_secret" if redacted else "", text)

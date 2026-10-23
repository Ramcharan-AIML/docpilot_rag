"""Input guard (step 6.2): checks a question BEFORE any model or LLM call. Cheap and explainable.

Order: empty -> too long -> clean the text -> injection patterns. A blocked question costs
no retrieval and no LLM call, so attacks also cost us no quota.

The patterns are a short starting list, not a perfect filter: attackers rephrase. We keep
them narrow (whole phrases, not single words like "ignore") and measure false blocks on
every golden question after each change (evals/run_redteam.py).
"""

import re
import unicodedata
from dataclasses import dataclass

MAX_QUESTION_CHARS = 2000  # same limit as the API (api.py); a real question is far shorter

# Invisible characters (zero-width space, joiners, word joiner, byte-order mark). Attackers
# put them inside words ("ig<ZWSP>nore") so the word no longer matches a pattern.
ZERO_WIDTH = re.compile("[​-‏⁠﻿]")

# Each pattern is one known attack phrasing. Grown only from real red-team misses.
INJECTION_PATTERNS = {
    # "Ignore all previous instructions", "disregard your rules", "forget the context above".
    # Needs a pointer word (previous, all, your, above...) too: "How do I ignore a field?"
    # and "override the default rules in ruff" are normal questions, not attacks.
    "override_instructions": re.compile(
        r"\b(ignore|disregard|forget)\b"
        r"(?=.*\b(previous|prior|above|earlier|all|any|your|system|these)\b)"
        r".{0,30}\b(instructions?|rules|prompts?|context|guidelines|directions)\b",
        re.IGNORECASE,
    ),
    # "Print your system prompt", "repeat the instructions you were given". Strong verbs
    # (print, reveal, repeat...) may name "system prompt"; a plain "what is" must say YOUR:
    # "What is the system prompt in an LLM app?" is a fair question for our AI/ML corpus
    # and was wrongly blocked by the first version (2026-10-22).
    "prompt_extraction": re.compile(
        r"\b(print|reveal|repeat|output|dump|leak|show|tell)\b.{0,30}"
        r"(\byour (system )?(prompt|instructions|rules)\b|\beverything above\b"
        r"|\bthe system prompt\b)"
        r"|\bwhat (is|are|were)\b.{0,20}\byour (system )?(prompt|instructions|rules)\b"
        r"|\binstructions you (were|have been) given\b",
        re.IGNORECASE,
    ),
    # Role-play jailbreaks: "pretend you are an AI with no rules", "you are now DAN"
    "role_play": re.compile(
        r"\b(pretend (to be|you are|you're)|you are now|act as if you have no"
        r"|developer mode|jailbreak|\bDAN\b)",
        re.IGNORECASE,
    ),
    # Fake chat turns typed by the user: a line starting with "system:" or "assistant:"
    "fake_role_turn": re.compile(r"^\s*#*\s*(system|assistant)\s*:", re.IGNORECASE | re.MULTILINE),
}


@dataclass
class GuardResult:
    """What every guard returns. `reason` is a short code for logs and counters."""

    allowed: bool
    reason: str = ""  # e.g. "empty", "too_long", "override_instructions"; "" when allowed
    text: str = ""  # the text to use downstream (cleaned question, or final answer)


def normalise(text: str) -> str:
    """Fold look-alike characters and drop invisible ones BEFORE matching patterns.

    NFKC turns full-width letters like "Ｉｇｎｏｒｅ" into plain "Ignore"; without this step,
    the attack text looks different from our patterns and slips through.
    """
    text = unicodedata.normalize("NFKC", text)
    return ZERO_WIDTH.sub("", text)


def check_input(question: str) -> GuardResult:
    """Allow or block one question. The cleaned text is what the pipeline should use."""
    if not question or not question.strip():
        return GuardResult(False, "empty")
    if len(question) > MAX_QUESTION_CHARS:
        return GuardResult(False, "too_long")

    cleaned = normalise(question).strip()
    for name, pattern in INJECTION_PATTERNS.items():
        if pattern.search(cleaned):
            return GuardResult(False, name)
    return GuardResult(True, text=cleaned)

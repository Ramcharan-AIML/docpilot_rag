"""Query transforms (step 3.6): let the LLM rewrite the question BEFORE we search.

| Name      | What the LLM writes                       | What we search with              |
|-----------|-------------------------------------------|----------------------------------|
| multi     | 3 rewrites of the question                | the question + each rewrite      |
| hyde      | a short fake answer passage               | the question + the fake passage  |
| stepback  | one more general question                 | the question + the general one   |
| decompose | up to 3 simple sub-questions              | the question + each sub-question |

Every transform is ONE LLM call. The original question is always searched too, so a bad
rewrite can add noise but cannot remove what the plain search found. The lists are merged
with RRF; the reranker then scores against the ORIGINAL question.
"""

import re
from collections.abc import Callable

from docpilot import config
from docpilot.llm.client import chat, get_llm_client

# Change this whenever a prompt changes: it is part of the cache key (evals/cache/).
PROMPT_VERSION = "qt-v1"
MAX_LINES = 3

SYSTEM = (
    "You help a search engine for technical documentation (FastAPI, Pydantic, Docker, "
    "AI/ML concepts, interview preparation). Follow the format exactly. No preamble."
)
PROMPTS = {
    "multi": (
        "Write 3 different rewrites of the question below. Use other words and the technical "
        "terms the documentation would likely use. One rewrite per line, no numbering.\n\n"
        "Question: {question}"
    ),
    "hyde": (
        "Write a short passage (3 to 5 sentences) that could appear in technical "
        "documentation and answers the question below. If you are not sure, still write a "
        "plausible passage: it is only used for search, never shown to a user.\n\n"
        "Question: {question}"
    ),
    "stepback": (
        "Write ONE more general question behind the question below: the concept or topic "
        "it depends on. Only the question, on one line.\n\nQuestion: {question}"
    ),
    "decompose": (
        "If the question below has several parts, split it into simple sub-questions, one "
        "per line, at most 3. If it is already simple, repeat it unchanged on one line.\n\n"
        "Question: {question}"
    ),
}
TRANSFORMS = tuple(PROMPTS)
# HyDE's output is a PASSAGE, not a question: embed it like a chunk (no BGE query prefix).
PASSAGE_STYLE = {"hyde"}

# (system, user) -> reply text. A parameter, so tests can pass a fake LLM.
Ask = Callable[[str, str], str]


def default_ask() -> Ask:
    """The real LLM from .env (config.LLM_PROVIDER / LLM_MODEL)."""
    client = get_llm_client()
    return lambda system, user: chat(client, system, user)


def clean_lines(reply: str) -> list[str]:
    """LLM reply -> list of lines, without numbering, bullets or quotes."""
    lines = []
    for line in reply.splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip().strip('"').strip()
        if line:
            lines.append(line)
    return lines


def transform(name: str, question: str, ask: Ask) -> list[str]:
    """The new search texts for `question` (the original is NOT included)."""
    if name not in PROMPTS:
        raise ValueError(f"Unknown transform {name!r}. Choose one of: {TRANSFORMS}")
    reply = ask(SYSTEM, PROMPTS[name].format(question=question))
    if name == "hyde":
        return [" ".join(clean_lines(reply))]  # one passage, even if the LLM used lines
    lines = clean_lines(reply)
    if name == "stepback":
        lines = lines[:1]
    return lines[:MAX_LINES]


def search_texts(name: str, question: str, new_texts: list[str]) -> list[tuple[str, bool]]:
    """What to search with: (text, is_passage) for the original + each new text."""
    is_passage = name in PASSAGE_STYLE
    texts = [(question, False)]
    for text in new_texts:
        if text.strip().lower() != question.strip().lower():  # skip exact repeats
            texts.append((text, is_passage))
    return texts


def model_tag() -> str:
    """LLM model name made safe for a file name: openai/gpt-oss-120b -> openai_gpt-oss-120b."""
    return re.sub(r"[^A-Za-z0-9.-]+", "_", config.LLM_MODEL or "no-model")

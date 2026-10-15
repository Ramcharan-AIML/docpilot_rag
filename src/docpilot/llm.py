"""One OpenAI-compatible chat client for several free providers (D-004, D-028).

Groq, OpenRouter, Gemini and Ollama all speak the same "OpenAI chat" format, so one client
library works for all of them: only the base URL and the key change. The provider is a
setting in .env, not code.
"""

import os

from openai import OpenAI  # the library only; no OpenAI account is used

from docpilot import config

# provider -> (base URL, name of the env var holding the key)
# Groq URL checked 2026-10-12 (D-028). The others are not used yet: check them on the day
# we first switch to them.
PROVIDERS: dict[str, tuple[str, str | None]] = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY"),
    "ollama": (os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"), None),
}


def get_llm_client(provider: str | None = None) -> OpenAI:
    """Build a client for `provider` (default: LLM_PROVIDER from .env)."""
    provider = provider or config.LLM_PROVIDER
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown LLM_PROVIDER {provider!r}. Choose one of: {list(PROVIDERS)}")

    base_url, key_name = PROVIDERS[provider]
    api_key = os.getenv(key_name) if key_name else "ollama"  # Ollama ignores the key
    if not api_key:
        raise RuntimeError(f"{key_name} is missing. Copy .env.example to .env and fill it.")
    # The library retries 429 (rate limit) and 5xx errors twice by itself (max_retries=2).
    return OpenAI(base_url=base_url, api_key=api_key, timeout=config.LLM_TIMEOUT_SECONDS)


def chat(client: OpenAI, system: str, user: str, model: str | None = None) -> str:
    """Send one system + user message, return the reply text."""
    # Read the setting now, not as a default argument: defaults are frozen at import time.
    model = model or config.LLM_MODEL
    if not model:
        raise RuntimeError("LLM_MODEL is empty. Set it in .env (see docs/decisions.md D-028).")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},  # the rules
            {"role": "user", "content": user},  # the question (+ context, from rag.py)
        ],
        temperature=0,  # same input -> (almost) same output; needed for fair evals
    )
    choice = response.choices[0]
    answer = choice.message.content or ""
    if not answer.strip():
        # Reasoning models (gpt-oss) can spend the whole token budget thinking and return
        # no answer. Fail loudly: an empty string would be counted as a wrong answer.
        raise RuntimeError(f"Empty answer from {model} (finish_reason={choice.finish_reason!r})")
    return answer

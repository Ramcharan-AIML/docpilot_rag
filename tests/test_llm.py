"""Tests for llm.py with a fake client: no network, no key used, no free quota spent."""

from types import SimpleNamespace

import pytest

from docpilot import config
from docpilot.llm.client import chat, get_llm_client


class FakeClient:
    """Looks like OpenAI() from the outside: client.chat.completions.create(...)."""

    def __init__(self, content: str | None, finish_reason: str = "stop") -> None:
        self.sent: dict = {}  # what chat() passed in, so tests can check it
        reply = SimpleNamespace(
            message=SimpleNamespace(content=content), finish_reason=finish_reason
        )
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self._response = SimpleNamespace(choices=[reply])

    def _create(self, **kwargs):
        self.sent = kwargs
        return self._response


def test_chat_returns_text_and_sends_system_then_user() -> None:
    fake = FakeClient("FastAPI uses type hints [1].")

    answer = chat(fake, "rules", "question", model="some-model")

    assert answer == "FastAPI uses type hints [1]."
    assert [m["role"] for m in fake.sent["messages"]] == ["system", "user"]
    assert fake.sent["temperature"] == 0
    assert fake.sent["model"] == "some-model"


def test_empty_answer_raises() -> None:
    fake = FakeClient(content=None, finish_reason="length")

    with pytest.raises(RuntimeError, match="length"):
        chat(fake, "rules", "question", model="some-model")


def test_empty_model_setting_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "LLM_MODEL", "")

    with pytest.raises(RuntimeError, match="LLM_MODEL"):
        chat(FakeClient("hi"), "rules", "question")


def test_unknown_provider_raises() -> None:
    with pytest.raises(ValueError, match="Unknown"):
        get_llm_client("not-a-provider")


def test_missing_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)  # only inside this test

    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        get_llm_client("groq")

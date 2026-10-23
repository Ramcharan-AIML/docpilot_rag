"""Chat memory (D-061): make follow-up questions work.

Problem: search only sees the latest message. "What about the second one?" or "Explain it
simpler" find nothing, and "What was my last question?" is not in any document.

Fix ("condense", the standard conversational-RAG step): ONE small LLM call rewrites the
latest message into a standalone question, using the last few turns. If the message is
about the conversation itself, the model answers "CHAT" and we answer from the history.
The first message of a chat has no history, so it costs no extra call.

Why not send the whole history to search: old turns pull search off-topic. Why not skip the
LLM and use rules ("it" -> last noun): rules break on real follow-ups.
"""

from openai import OpenAI

from docpilot import config
from docpilot.llm.client import chat

ABOUT_CHAT = "CHAT"  # the rewriter's answer when the question is about the conversation
MESSAGE_CHARS = 600  # long answers are cut in the history: the gist is enough

CONDENSE_SYSTEM = f"""You rewrite the user's LATEST message into one standalone question for a
document search. Use the conversation only to resolve references like "it", "that", "the
second one", "explain more".
Rules:
- If the latest message is already standalone, repeat it unchanged.
- If it asks about the conversation itself (for example "what was my last question?",
  "summarise our chat", "what did you just say?"), reply exactly: {ABOUT_CHAT}
- Never answer the question. Reply with the question only, on one line."""

ABOUT_CHAT_SYSTEM = """Answer the user's question about THIS conversation, using only the
conversation below. Be short and exact. Do not add facts from outside the conversation."""


def format_history(messages: list[dict], turns: int = config.HISTORY_TURNS) -> str:
    """The last `turns` messages as "User: ..." / "Assistant: ..." lines."""
    lines = []
    for message in messages[-turns:]:
        speaker = "User" if message["role"] == "user" else "Assistant"
        text = " ".join(message["content"].split())
        if len(text) > MESSAGE_CHARS:
            text = text[:MESSAGE_CHARS] + " ..."
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


def condense(question: str, history: list[dict], llm_client: OpenAI) -> tuple[str, bool]:
    """(standalone question, is_about_the_chat). No history: no LLM call."""
    if not history:
        return question, False
    prompt = f"Conversation:\n{format_history(history)}\n\nLatest message: {question}"
    rewritten = chat(llm_client, CONDENSE_SYSTEM, prompt).strip().splitlines()[0].strip()
    if rewritten.strip(" .\"'").upper() == ABOUT_CHAT:
        return question, True
    return rewritten or question, False


def answer_about_chat(question: str, history: list[dict], llm_client: OpenAI) -> str:
    prompt = f"Conversation:\n{format_history(history)}\n\nQuestion: {question}"
    return chat(llm_client, ABOUT_CHAT_SYSTEM, prompt)

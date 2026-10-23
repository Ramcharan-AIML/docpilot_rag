"""Talks to the DocPilot API, and formats its answers for the screen (D-060).

No Streamlit here, so every function can be unit-tested (tests/test_ui_client.py).
The UI never imports docpilot: it is a separate small app that only knows the API's URL,
so later it can run in its own container without torch or the models.
"""

import os

import requests

API_URL = os.getenv("DOCPILOT_API_URL", "http://127.0.0.1:8000")  # 127.0.0.1, never localhost
ASK_TIMEOUT = 120  # seconds: search + rerank + LLM, plus free-tier rate-limit waits
UPLOAD_TIMEOUT = 600  # seconds: Docling reads about 4 s per page, limit 30 pages

STAGE_NAMES = {
    "input_guard": "Input guard",
    "embed_query": "Embed question",
    "search": "Search (hybrid)",
    "rerank": "Rerank",
    "llm": "LLM answer",
    "output_guard": "Output guard",
    "total": "Total",
}

STATUS_NOTES = {
    "blocked_input": "Blocked by the input guard (this looked like an attack).",
    "blocked_output": "The answer failed the output check (no valid citation), so it was refused.",
    "not_found": "The documents do not contain this answer.",
}


class ApiError(Exception):
    """A message that is safe and useful to show the user."""


def error_message(response: requests.Response) -> str:
    """FastAPI puts its reason in {"detail": ...}; fall back to the status code."""
    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = None
    if isinstance(detail, str):
        return detail
    return f"API error {response.status_code}"


def call(method: str, path: str, base: str = API_URL, timeout: int = 30, **kwargs) -> dict:
    """One HTTP call; turns every failure into an ApiError with a readable message."""
    try:
        response = requests.request(method, f"{base}{path}", timeout=timeout, **kwargs)
    except requests.ConnectionError as error:
        raise ApiError(f"Cannot reach the API at {base}. Is uvicorn running?") from error
    except requests.Timeout as error:
        raise ApiError(f"The API did not answer within {timeout} s.") from error
    if not response.ok:
        raise ApiError(error_message(response))
    return response.json()


def is_api_up(base: str = API_URL) -> bool:
    try:
        return call("GET", "/health", base, timeout=3).get("status") == "ok"
    except ApiError:
        return False


def ask(question: str, library: str, base: str = API_URL) -> dict:
    body = {"question": question, "library": library}
    return call("POST", "/ask", base, timeout=ASK_TIMEOUT, json=body)


def upload(filename: str, data: bytes, base: str = API_URL) -> dict:
    files = {"file": (filename, data, "application/pdf")}
    return call("POST", "/upload", base, timeout=UPLOAD_TIMEOUT, files=files)


def list_uploads(base: str = API_URL) -> dict[str, int]:
    return call("GET", "/uploads", base)["documents"]


def status_note(status: str) -> str:
    """A short explanation under the answer; "" for a normal answer."""
    return STATUS_NOTES.get(status, "")


def timing_rows(timings_ms: dict[str, float]) -> list[dict]:
    """[{"Stage": "Rerank", "ms": 485.0}, ...] in pipeline order, unknown stages last."""
    order = list(STAGE_NAMES)
    stages = sorted(timings_ms, key=lambda s: order.index(s) if s in order else len(order))
    return [{"Stage": STAGE_NAMES.get(s, s), "ms": round(timings_ms[s], 1)} for s in stages]


def source_rows(sources: list[dict]) -> list[dict]:
    """Numbered like the citations: [1] is the first source the LLM saw."""
    return [
        {"Cite": f"[{n}]", "Document": s["source"], "Chunk": s["chunk_number"]}
        for n, s in enumerate(sources, start=1)
    ]

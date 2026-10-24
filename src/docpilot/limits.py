"""Rate limits for the public link (Phase 7 A2, D-063): "at most N per window, per key".

Raw first (Rule 8): a fixed-window counter in a Python dict, no Redis. Fixed window =
count per clock minute / per UTC day, reset when the window changes.

Real-life example: a free water tap with a rule "3 bottles per person per minute".

Honest limits of this version:
- The counts live in this process's memory: a restart resets them, and two API processes
  would each count separately. Redis (shared, survives restarts) is the Stage D upgrade.
- Fixed window allows a burst at the edge (3 at 0:59 + 3 at 1:01). A token bucket is
  smoother; for a demo, simple wins.
"""

import threading
import time

from docpilot import config

# FastAPI runs plain `def` endpoints in a thread pool: two requests can count at the same
# moment, so every read-and-update happens under one lock.
_lock = threading.Lock()
_counts: dict[tuple, tuple[int, int]] = {}  # (kind, key, seconds) -> (window number, count)
MAX_KEYS = 50_000  # forget everything past this many entries: memory stays small

BUSY = "DocPilot is busy right now (free demo). Please try again in a minute."
MESSAGES = {
    ("site", 60): BUSY,
    ("site", 86_400): "DocPilot reached today's free quota. Please come back tomorrow.",
    60: "Limit reached: please wait a minute before the next one.",
    86_400: "Daily limit reached for this free demo. Please come back tomorrow.",
}


def _refused(limits: dict[str, list[tuple[int, int]]], keys: dict[str, str], now: float):
    """Count one request against every (limit, window) of every kind, or name the first
    limit that refuses it as (kind, seconds).

    Checks ALL first and counts only when all allow: a refused request must not use up
    quota (otherwise someone at the limit would stay locked out longer).
    """
    slots = []
    for kind, rules in limits.items():
        for limit, seconds in rules:
            window = int(now // seconds)  # minute number or UTC day number since 1970
            slot = (kind, keys[kind], seconds)
            seen_window, count = _counts.get(slot, (window, 0))
            if seen_window != window:
                count = 0  # a new minute / day: start again
            if count >= limit:
                return kind, seconds
            slots.append((slot, window, count))
    for slot, window, count in slots:
        _counts[slot] = (window, count + 1)
    if len(_counts) > MAX_KEYS:
        _counts.clear()  # rare; at worst a few people get a fresh window early
    return None


def _message(refusal) -> str | None:
    if refusal is None:
        return None
    return MESSAGES.get(refusal) or MESSAGES[refusal[1]]


def question_refusal(visitor: str, ip: str, now: float | None = None) -> str | None:
    """None = go ahead (and it is counted); otherwise the message to show.
    Always None outside PUBLIC_MODE (the laptop is unlimited)."""
    if not config.PUBLIC_MODE:
        return None
    keys = {"visitor": visitor, "ip": ip, "site": "site"}
    with _lock:
        return _message(_refused(config.QUESTION_LIMITS, keys, now or time.time()))


def upload_refusal(ip: str, now: float | None = None) -> str | None:
    if not config.PUBLIC_MODE:
        return None
    with _lock:
        return _message(_refused(config.UPLOAD_LIMITS, {"ip": ip}, now or time.time()))


def reset() -> None:
    """For tests."""
    with _lock:
        _counts.clear()


# --- A3: concurrency cap (a barber shop with 2 chairs and a waiting bench) ---
# A semaphore is a counter of free seats: acquire() takes one (or waits), release() gives it
# back. Bounded = releasing more than was taken is an error, so a bug cannot add chairs.
# Why: 20 answers at once = 20 reranker runs on 2 CPUs and 2 GB RAM; with 2 seats, extra
# traffic becomes waiting time, not a crash.
_answer_seats = threading.BoundedSemaphore(config.MAX_CONCURRENT_ANSWERS)


def take_answer_seat(wait_seconds: float) -> bool:
    """True = a seat is ours (give it back with free_answer_seat). False = still full."""
    return _answer_seats.acquire(timeout=wait_seconds)


def free_answer_seat() -> None:
    _answer_seats.release()

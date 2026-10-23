"""Tests for the public-mode rate limits (A2) and answer seats (A3). Time is passed in, so
no test waits."""

import threading

import pytest

from docpilot import config, limits

MINUTE_START = 1_800_000_000.0  # some moment exactly at the start of a minute (a multiple of 60)


@pytest.fixture(autouse=True)
def public_mode(monkeypatch):
    monkeypatch.setattr(config, "PUBLIC_MODE", True)
    monkeypatch.setattr(
        config,
        "QUESTION_LIMITS",
        {"visitor": [(2, 60), (3, 86_400)], "ip": [(5, 60)], "site": [(4, 60)]},
    )
    limits.reset()
    yield
    limits.reset()


def ask(visitor="v1", ip="1.1.1.1", at=MINUTE_START):
    return limits.question_refusal(visitor, ip, now=at)


def test_laptop_mode_is_unlimited(monkeypatch) -> None:
    monkeypatch.setattr(config, "PUBLIC_MODE", False)
    assert all(ask() is None for _ in range(100))


def test_third_question_in_a_minute_is_refused_then_allowed_next_minute() -> None:
    assert ask() is None and ask(at=MINUTE_START + 1) is None
    assert ask(at=MINUTE_START + 59) == limits.MESSAGES[60]
    assert ask(at=MINUTE_START + 60) is None  # a new minute starts again (day count: 3)


def test_daily_limit_counts_across_minutes() -> None:
    for minute in range(3):
        assert ask(at=MINUTE_START + 60 * minute) is None
    assert ask(at=MINUTE_START + 60 * 5) == limits.MESSAGES[86_400]


def test_a_refused_request_does_not_use_up_quota() -> None:
    ask(), ask()
    for _ in range(10):
        ask()  # refused: must not count towards the day
    assert ask(at=MINUTE_START + 60) is None  # the day's 3rd question still works


def test_site_limit_covers_everyone() -> None:
    # 4 different visitors on 4 addresses: the site's 4 per minute is used up.
    for n in range(4):
        assert ask(visitor=f"v{n}", ip=f"10.0.0.{n}") is None
    assert ask(visitor="new", ip="10.0.0.99") == limits.MESSAGES[("site", 60)]


def test_new_visitor_id_does_not_reset_the_ip_limit(monkeypatch) -> None:
    monkeypatch.setitem(config.QUESTION_LIMITS, "ip", [(2, 60)])
    assert ask(visitor="a") is None and ask(visitor="b") is None
    assert ask(visitor="c") == limits.MESSAGES[60]  # cleared browser, same address


def test_two_seats_then_the_third_waits(monkeypatch) -> None:
    monkeypatch.setattr(limits, "_answer_seats", threading.BoundedSemaphore(2))
    assert limits.take_answer_seat(0) and limits.take_answer_seat(0)
    assert not limits.take_answer_seat(0.01)  # full: gives up after the wait
    limits.free_answer_seat()
    assert limits.take_answer_seat(0)
    limits.free_answer_seat(), limits.free_answer_seat()
    with pytest.raises(ValueError):
        limits.free_answer_seat()  # bounded: a bug cannot add a third chair


def test_upload_limit_per_ip(monkeypatch) -> None:
    monkeypatch.setattr(config, "UPLOAD_LIMITS", {"ip": [(1, 86_400)]})
    assert limits.upload_refusal("1.1.1.1", now=MINUTE_START) is None
    assert limits.upload_refusal("1.1.1.1", now=MINUTE_START) == limits.MESSAGES[86_400]
    assert limits.upload_refusal("2.2.2.2", now=MINUTE_START) is None

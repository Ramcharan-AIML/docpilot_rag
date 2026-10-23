"""Tests for the red-team runner's scoring. Made-up answers; no model, no LLM, no Qdrant."""

from docpilot import config
from docpilot.guardrails.output_guard import CANARY
from evals.run_redteam import (
    attack_succeeded,
    load_attacks,
    poisoned_retrieve,
    stopped_by,
    summarise,
)


def test_attack_file_is_valid() -> None:
    attacks = load_attacks()
    ids = [attack["id"] for attack in attacks]
    assert len(ids) == len(set(ids))  # no duplicate ids
    for attack in attacks:
        assert attack["question"] and attack["category"] and attack["marker"]


def test_markers() -> None:
    pwned = {"marker": "PWNED"}
    assert attack_succeeded(pwned, "PWNED")
    assert not attack_succeeded(pwned, config.BLOCKED_PHRASE)

    leak = {"marker": "leak"}
    assert attack_succeeded(leak, f"my marker is {CANARY}")
    assert attack_succeeded(leak, "Rule: Use ONLY the numbered context.")  # old prompt, no canary
    assert not attack_succeeded(leak, "I can't share that.")

    off_topic = {"marker": "answered"}
    assert attack_succeeded(off_topic, "Roses are red...")
    assert not attack_succeeded(off_topic, config.NOT_FOUND_PHRASE)
    assert not attack_succeeded(off_topic, config.BLOCKED_PHRASE)


def test_stopped_by_names_the_layer() -> None:
    assert stopped_by({"status": "blocked_input"}, success=False) == "input_guard"
    assert stopped_by({"status": "blocked_output"}, success=False) == "output_guard"
    assert stopped_by({"status": "not_found"}, success=False) == "prompt/model"
    assert stopped_by({"status": "ok"}, success=True) == "-"


def test_summarise_counts_per_mode_and_category() -> None:
    rows = [
        {"mode": "before", "category": "a", "success": True},
        {"mode": "before", "category": "b", "success": True},
        {"mode": "after", "category": "a", "success": False},
        {"mode": "after", "category": "b", "success": True},
    ]
    after = summarise(rows, "after")
    assert after["successes"] == 1
    assert after["success_rate"] == 0.5
    assert after["per_category"] == {"a": "0/1", "b": "1/1"}


def test_poison_goes_to_rank_one_and_only_once() -> None:
    real_hits = [{"text": f"chunk {i}", "source": "x.md"} for i in range(config.TOP_K)]

    def real_retrieve(question, client, settings, timings=None):
        return list(real_hits)

    first = poisoned_retrieve(real_retrieve, "POISON A")
    second = poisoned_retrieve(real_retrieve, "POISON B")  # built after the first: no stacking
    hits = second("q", None, None)

    assert hits[0]["text"] == "POISON B"
    assert [hit["text"] for hit in hits].count("POISON A") == 0
    assert len(hits) == config.TOP_K  # the LLM still gets TOP_K chunks
    assert first("q", None, None)[0]["text"] == "POISON A"

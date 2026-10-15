"""Tests for evals/matching.py: when does a retrieved chunk count as a hit?"""

from evals.matching import normalise, relevance_list, snippet_in_chunk

SNIPPET = "set their default to `None`"


def test_normalise_squashes_case_and_whitespace():
    assert normalise("  Set   THEIR\n default ") == "set their default"


def test_snippet_found_despite_line_break_and_case():
    chunk = "You can declare optional query parameters, by setting Their\ndefault to `None`:"
    assert snippet_in_chunk("setting their default to `None`", chunk)


def test_snippet_cut_by_chunk_boundary_still_counts():
    # The chunk ends after 22 of the 27 characters (81% >= 70%): a boundary cut, not a miss.
    chunk = "...optional query parameters, by setting their default to `N"
    assert snippet_in_chunk(SNIPPET, chunk)


def test_small_piece_of_snippet_is_not_a_hit():
    # Only "set their" (9 of 27 characters, 33%) is in the chunk.
    assert not snippet_in_chunk(SNIPPET, "please set their names here")


def test_relevance_list_marks_the_right_rank():
    hits = [
        {"source": "a.md", "text": "nothing useful"},
        {"source": "a.md", "text": "you must set their default to `None` here"},
    ]
    evidence = [{"doc": "a.md", "snippet": SNIPPET}]
    assert relevance_list(hits, evidence) == [0, 1]


def test_same_text_in_another_document_is_not_a_hit():
    hits = [{"source": "b.md", "text": "set their default to `None`"}]
    assert relevance_list(hits, [{"doc": "a.md", "snippet": SNIPPET}]) == [0]


def test_snippet_repeated_by_chunk_overlap_counts_once():
    # Two neighbouring chunks both contain the snippet (100-char overlap); one point only.
    hits = [{"source": "a.md", "text": f"... {SNIPPET} ..."}] * 2
    assert relevance_list(hits, [{"doc": "a.md", "snippet": SNIPPET}]) == [1, 0]


def test_two_snippets_in_two_chunks_both_count():
    hits = [
        {"source": "a.md", "text": "first fact here"},
        {"source": "a.md", "text": "second fact here"},
    ]
    evidence = [{"doc": "a.md", "snippet": "second fact"}, {"doc": "a.md", "snippet": "first fact"}]
    assert relevance_list(hits, evidence) == [1, 1]

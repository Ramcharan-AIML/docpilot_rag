"""Decide whether a retrieved chunk contains a gold evidence snippet (D-010)."""

from difflib import SequenceMatcher

# A snippet counts as found if at least this share of it sits in one chunk, in one piece.
# Recorded with every result: changing it changes the scores.
MIN_OVERLAP = 0.7


def normalise(text: str) -> str:
    """Lowercase and squash all whitespace, so line breaks do not cause misses."""
    return " ".join(text.lower().split())


def snippet_in_chunk(snippet: str, chunk_text: str, min_overlap: float = MIN_OVERLAP) -> bool:
    """True if the snippet is inside the chunk, or most of it is.

    The 'most of it' part handles a snippet cut in half by a chunk boundary: the longest
    common piece must cover at least `min_overlap` of the snippet.
    """
    snippet_n, chunk_n = normalise(snippet), normalise(chunk_text)
    if snippet_n in chunk_n:
        return True  # the normal case, and much faster than the matcher below
    # autojunk=False: the default heuristic ignores common characters in texts over
    # 200 chars, which would make long chunks match worse than short ones.
    matcher = SequenceMatcher(None, snippet_n, chunk_n, autojunk=False)
    match = matcher.find_longest_match(0, len(snippet_n), 0, len(chunk_n))
    return match.size / max(len(snippet_n), 1) >= min_overlap


def relevance_list(
    retrieved: list[dict], evidence: list[dict], min_overlap: float = MIN_OVERLAP
) -> list[int]:
    """One 0/1 per retrieved chunk, in rank order.

    Each gold snippet is counted once only: with 100-character overlap, two neighbouring
    chunks can both contain the same snippet, and counting it twice would inflate scores.
    """
    found: set[int] = set()  # indexes of evidence items already matched
    relevance = []
    for hit in retrieved:
        is_relevant = 0
        for index, item in enumerate(evidence):
            if index in found or hit["source"] != item["doc"]:
                continue  # already counted, or a different document
            if snippet_in_chunk(item["snippet"], hit["text"], min_overlap):
                found.add(index)
                is_relevant = 1
                break  # one chunk earns at most one point
        relevance.append(is_relevant)
    return relevance

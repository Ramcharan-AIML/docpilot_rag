"""The corpus register (D-030, step 2.8): every source DocPilot may read, written once.

Each entry says what the source is, where it comes from, under which licence, which exact
version we use, when the licence was checked, and whether it may leave this laptop.
scripts/01_download_docs.py downloads exactly these versions; ingestion/metadata.py copies
domain/doc_type/version into every chunk; tests/test_sources.py fails if an entry has no
licence, no licence link or no visibility flag.

Keyed by the first folder under data/docs/ (fastapi, docker, ...).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceInfo:
    domain: str  # "docs" | "learning" | "interview" (D-030)
    topic: str  # what it is about, in a few words
    doc_type: str  # "tutorial" | "reference" | "guide" | "paper" | "article" | "notes"
    url: str  # where it comes from (repo, article, or local path for own work)
    version: str  # pinned git commit, arXiv version, Wikipedia revision ...
    licence: str
    licence_url: str
    checked: str  # date the licence and version were checked (YYYY-MM-DD)
    visibility: str  # "public" | "local_only" (non-open material never leaves the laptop)


DOMAINS = ("docs", "learning", "interview")

SOURCES: dict[str, SourceInfo] = {
    # --- Group A: official technical docs ---
    "fastapi": SourceInfo(
        domain="docs",
        topic="FastAPI tutorial (4 pages)",
        doc_type="tutorial",
        url="https://github.com/fastapi/fastapi/tree/master/docs/en/docs/tutorial",
        version="d62354434b2e508fe89024213b220ca8e67dea5e",  # D-029
        licence="MIT",
        licence_url="https://github.com/fastapi/fastapi/blob/master/LICENSE",
        checked="2026-10-12",
        visibility="public",
    ),
    "pydantic": SourceInfo(
        domain="docs",
        topic="Pydantic concepts: configuration, strict mode, aliases (3 pages)",
        doc_type="guide",
        url="https://github.com/pydantic/pydantic/tree/main/docs/concepts",
        version="471fe56b45a85c9066fd8392e31dfad1402e071a",  # latest commit 2026-10-20
        licence="MIT",
        licence_url="https://github.com/pydantic/pydantic/blob/main/LICENSE",
        checked="2026-10-20",
        visibility="public",
    ),
    "docker": SourceInfo(
        domain="docs",
        topic="Docker concepts: containers, images, Dockerfile, ports, volumes (5 pages)",
        doc_type="guide",
        url="https://github.com/docker/docs/tree/main/content/get-started/docker-concepts",
        version="95b8ec69e3ea6cb682c587afa527aa658cf06dc0",  # latest commit 2026-10-20
        licence="Apache-2.0",
        licence_url="https://github.com/docker/docs/blob/main/LICENSE",
        checked="2026-10-20",
        visibility="public",
    ),
    # --- Group B: open-licence AI/ML learning material ---
    "cot": SourceInfo(
        domain="learning",
        topic="Chain-of-Thought prompting paper (Wei et al.), D-044",
        doc_type="paper",
        url="https://arxiv.org/abs/2201.11903",
        version="arXiv 2201.11903v6 (2023-01-10)",  # the download checks its sha256
        licence="CC BY 4.0 (Wei et al.: Chain-of-Thought Prompting Elicits Reasoning in LLMs)",
        licence_url="https://creativecommons.org/licenses/by/4.0/",
        checked="2026-10-20",
        visibility="public",
    ),
    "wikipedia": SourceInfo(
        domain="learning",
        topic="Wikipedia: RAG, word embedding, IR evaluation measures (3 articles)",
        doc_type="article",
        url="https://en.wikipedia.org/wiki/",
        # One pinned revision per article: see WIKIPEDIA_REVISIONS in 01_download_docs.py.
        version="revisions 1381095247, 1374850731, 1375531235",
        licence="CC BY-SA 4.0 (Wikipedia contributors)",
        licence_url="https://creativecommons.org/licenses/by-sa/4.0/",
        checked="2026-10-20",
        visibility="public",
    ),
    # --- Group C: interview prep (the learner's own notes = own work, public) ---
    "interview": SourceInfo(
        domain="interview",
        topic="Learner's interview notes: phases 0-3 (Markdown) + phase 1 (Word)",
        doc_type="notes",
        url="docs/interview/ (this repository)",
        version="git history of docs/interview/ is the version",
        licence="own work (project author)",
        licence_url="docs/interview/README.md",
        checked="2026-10-20",
        visibility="public",
    ),
}

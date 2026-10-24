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
    title: str = ""  # the name visitors see in the web UI's library panel (D-066)


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
        title="FastAPI",
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
        title="Pydantic",
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
        title="Docker",
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
        title="Chain-of-Thought paper",
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
        title="Wikipedia articles",
    ),
    # --- Group C: interview prep (the learner's own notes) ---
    # local_only since 2026-10-24 (D-066): the learner keeps personal notes off the public
    # site; the laptop library still has them (evals unchanged), the live snapshot does not.
    "interview": SourceInfo(
        domain="interview",
        topic="Learner's interview notes: phases 0-3 (Markdown) + phase 1 (Word)",
        doc_type="notes",
        url="docs/interview/ (this repository)",
        version="git history of docs/interview/ is the version",
        licence="own work (project author)",
        licence_url="docs/interview/README.md",
        checked="2026-10-20",
        visibility="local_only",
        title="Interview notes",
    ),
    # --- CI only: the eval gate's fixture corpus (step 2.10), never in the real index ---
    "ci_fixture": SourceInfo(
        domain="docs",
        topic="Lumen, a made-up task-queue library: 7 short pages for the CI eval gate",
        doc_type="guide",
        url="tests/fixtures/corpus/ci_fixture/ (this repository)",
        version="git history of tests/fixtures/corpus/ is the version",
        licence="own work (written for DocPilot, so licensing is never an issue)",
        licence_url="tests/fixtures/README.md",
        checked="2026-10-20",
        visibility="public",
        title="Lumen (CI fixture)",
    ),
}


# D-060: PDFs a user uploads in the UI. NOT in SOURCES on purpose: SOURCES is the curated,
# downloaded and evaluated corpus (01_download_docs.py and the golden-set checks loop over it).
# We do not know an uploaded file's licence, so it never leaves this laptop.
UPLOADS = SourceInfo(
    domain="uploads",
    topic="Files uploaded by the user in the web UI",
    doc_type="upload",
    url="uploaded through POST /upload",
    version="sha256 of the file (in the Docling cache meta)",
    licence="unknown (user's own file)",
    licence_url="n/a",
    checked="2026-10-23",
    visibility="local_only",
)

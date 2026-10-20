"""Facts about each document source, written once (step 2.5).

Step 2.8 grows this into the full corpus register (D-030): every source with its domain,
licence, version and visibility. For now: the one source we have.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceInfo:
    domain: str  # "docs" | "learning" | "interview" (D-030)
    doc_type: str  # "tutorial" | "reference" | "guide" | "notes"
    version: str  # docs version or git commit that was downloaded
    licence: str
    visibility: str  # "public" | "local_only" (D-030: non-open material never leaves the laptop)


# Keyed by technology = the first folder under data/docs/.
SOURCES: dict[str, SourceInfo] = {
    "fastapi": SourceInfo(
        domain="docs",
        doc_type="tutorial",  # all 4 pages are from docs/en/docs/tutorial
        # Pinned commit (D-029); scripts/01_download_docs.py downloads exactly this version.
        version="d62354434b2e508fe89024213b220ca8e67dea5e",
        licence="MIT",
        visibility="public",
    ),
    # Step 2.7 (D-044): first PDF, the Chain-of-Thought paper (replaced the RAGAS paper).
    # Licence checked on arxiv.org/abs/2201.11903 on 2026-10-20.
    "cot": SourceInfo(
        domain="learning",
        doc_type="paper",
        # scripts/01_download_docs.py downloads exactly this version and checks its sha256.
        version="arXiv 2201.11903v6 (2023-01-10)",
        licence="CC BY 4.0 (Wei et al.: Chain-of-Thought Prompting Elicits Reasoning in LLMs)",
        visibility="public",
    ),
    # Step 2.7 (D-043): first DOCX, built by scripts/make_notes_docx.py from the learner's
    # own docs/interview/phase_1_interview.md (own work, so public).
    "interview": SourceInfo(
        domain="interview",
        doc_type="notes",
        version="docs/interview/phase_1_interview.md (git history is the version)",
        licence="own work (project author)",
        visibility="public",
    ),
}

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
}

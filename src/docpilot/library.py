"""What is in the demo library, for the web UI's library panel (D-066).

Built from what is REALLY in the main Qdrant collection (chunk counts per source), joined
with the corpus register (ingestion/sources.py) for titles and licences. So the panel can
never list a document the live site does not have: the laptop shows the interview notes,
the live site (whose snapshot leaves them out) does not.
"""

from pathlib import PurePosixPath

from docpilot.ingestion.metadata import technology_of
from docpilot.ingestion.sources import SOURCES

KINDS = {"docs": "Official docs", "learning": "Learning material", "interview": "Notes"}


def pretty_name(source: str) -> str:
    """'fastapi/query-params.md' -> 'Query params' (also '_' -> ' ' for Wikipedia names)."""
    stem = PurePosixPath(source).stem.replace("_", " ").replace("-", " ")
    return stem[:1].upper() + stem[1:]


def describe(chunk_counts: dict[str, int]) -> list[dict]:
    """{source: chunks} -> one entry per source group, in the register's order."""
    groups: dict[str, dict[str, int]] = {}
    for source, count in chunk_counts.items():
        groups.setdefault(technology_of(source), {})[source] = count
    entries = []
    for key, info in SOURCES.items():
        if key not in groups:
            continue
        files = groups[key]
        entries.append(
            {
                "key": key,
                "title": info.title or key,
                "kind": KINDS.get(info.domain, info.domain),
                "topic": info.topic,
                "documents": sorted(pretty_name(source) for source in files),
                "chunks": sum(files.values()),
                "licence": info.licence,
                "licence_url": info.licence_url,
                "url": info.url,
            }
        )
    return entries

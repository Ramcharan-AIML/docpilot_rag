"""Read documents from a folder into Document objects.

.md and .txt are read as they are; .pdf and .docx are converted to Markdown by Docling
first (step 2.7, ingestion/document_loader.py), so everything after the loader sees text.
"""

from dataclasses import dataclass
from pathlib import Path

from docpilot.ingestion.document_loader import CONVERTED_SUFFIXES, convert_to_markdown

TEXT_SUFFIXES = {".md", ".txt"}
SUPPORTED_SUFFIXES = TEXT_SUFFIXES | CONVERTED_SUFFIXES


@dataclass
class Document:
    text: str
    source: str  # path relative to the docs folder, e.g. "fastapi/query-params.md"


def read_text(path: Path, source: str) -> str:
    """The text the pipeline sees for one file (the golden validator uses it too)."""
    if path.suffix.lower() in CONVERTED_SUFFIXES:
        return convert_to_markdown(path, source)
    return path.read_text(encoding="utf-8")


def load_documents(folder: Path) -> list[Document]:
    """Load every supported file under `folder` (subfolders too), in a stable order."""
    if not folder.is_dir():
        # Fail loudly: an empty result here would quietly build an empty index later.
        raise FileNotFoundError(f"Docs folder not found: {folder}")

    documents: list[Document] = []
    for path in folder.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue  # skips folders, .gitkeep, images, anything we cannot read as text
        # as_posix() gives forward slashes on Windows too, so sources look the same everywhere
        source = path.relative_to(folder).as_posix()
        documents.append(Document(text=read_text(path, source), source=source))

    # Sort by the source string, not by Path: Windows compares paths ignoring case, Linux
    # does not, so sorting Paths could give a different order in CI. Same input must give
    # the same chunks in the same order on every machine, or eval numbers drift.
    documents.sort(key=lambda doc: doc.source)
    return documents

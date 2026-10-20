"""Turn PDF and Word (DOCX) files into Markdown with Docling (step 2.7, D-043).

One pipeline, many inputs: after conversion, a PDF goes through exactly the same cleaner,
blocks, chunkers and eval as a Markdown page. Docling reads the page LAYOUT (columns,
headings, tables) with small local models, so a table comes out as a Markdown table
instead of a jumble of numbers.

Settings (checked on docling 2.140.0, 2026-10-19):
- OCR off: our files are digital (text inside the PDF), and OCR is slow and not installed;
- table structure on: tables are why we use Docling (why not PyMuPDF: D-043).
Speed on this laptop's CPU: Chain-of-Thought paper, 43 pages, 182 s (about 4 s per page).
So every result is cached in data/processed/converted/, keyed by the file's sha256 and the
Docling version: a re-ingest costs nothing unless the file or Docling changed.
"""

import hashlib
import json
import time
from functools import lru_cache
from importlib.metadata import version
from pathlib import Path

from docpilot import config

CONVERTED_SUFFIXES = {".pdf", ".docx"}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def get_converter():
    """Build the Docling converter once (it loads layout + table models: seconds).

    Imported here, not at the top: Docling and torchvision are heavy, and the API and most
    tests never convert a file, so they should not pay for the import.
    """
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(do_ocr=False, do_table_structure=True)  # do_ocr defaults True
    return DocumentConverter(
        allowed_formats=[InputFormat.PDF, InputFormat.DOCX],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)},
    )


def convert_to_markdown(path: Path, source: str, cache_dir: Path | None = None) -> str:
    """Markdown text of a PDF or DOCX file, from the cache when nothing changed."""
    cache_dir = cache_dir or config.CONVERTED_DIR  # read now, not at import (tests change it)
    markdown_path = cache_dir / f"{source}.md"
    meta_path = cache_dir / f"{source}.meta.json"
    key = {"sha256": file_sha256(path), "docling": version("docling-slim")}
    if markdown_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if {name: meta.get(name) for name in key} == key:
            return markdown_path.read_text(encoding="utf-8")

    started = time.perf_counter()
    result = get_converter().convert(path)
    document = result.document
    markdown = document.export_to_markdown()
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")
    meta = {
        **key,
        "status": str(result.status),
        "pages": len(document.pages),  # 0 for DOCX: Word files have no fixed pages
        "tables": len(document.tables),
        "seconds": round(time.perf_counter() - started, 1),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    pages, tables, seconds = meta["pages"], meta["tables"], meta["seconds"]
    print(f"converted {source}: {pages} pages, {tables} tables, {seconds} s")
    return markdown

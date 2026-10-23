"""User uploads (D-060, D-061): one file in -> chunks in the uploads collection, for ONE chat.

Recipe: read text -> clean -> 200-token chunks -> metadata -> BGE + BM25 vectors -> Qdrant,
the same chunking and models as the main library. Differences, on purpose:
- FAST reader for PDFs (pypdfium2 text, about 3 ms per page) instead of Docling's layout
  models (about 4 s per page). Measured on the 43-page CoT paper: 10.8 s vs 182 s in total.
  Cost: tables come out as plain lines, not Markdown tables. Docling stays for the curated
  main library, where table quality was measured (D-043).
- Every page starts with a "# Page N" heading, so each chunk's heading_path names its page
  and citations can say "Page 3".
- Its own collection, and every point carries the chat's id: a chat searches only its own
  files, like a NotebookLM notebook. The measured main library never changes.

Uploaded text is untrusted: at question time the context guard boxes it like any chunk.
"""

import re
import time
from pathlib import Path

from qdrant_client import QdrantClient

from docpilot import config
from docpilot.embedding.dense import embed_documents
from docpilot.embedding.sparse import average_length, embed_sparse_documents
from docpilot.ingestion.chunkers.base import embedding_text
from docpilot.ingestion.chunkers.fixed import fixed_token_chunks
from docpilot.ingestion.cleaner import clean_markdown
from docpilot.ingestion.metadata import add_metadata
from docpilot.ingestion.sources import UPLOADS
from docpilot.store.qdrant_store import add_chunks, delete_source, ensure_collection

SOURCE_FOLDER = "uploads"  # sources look like "uploads/<chat id>/notes.pdf"


class UploadError(ValueError):
    """A file we refuse (wrong type, too big, too many pages). The message is user-safe."""


def safe_filename(name: str) -> str:
    """Keep letters, digits, dot, dash, underscore; drop any folder part.

    "../../secret/a b.pdf" -> "a_b.pdf": a user must never choose where we write a file.
    """
    name = Path(name.replace("\\", "/")).name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    if Path(name).suffix.lower() not in config.UPLOAD_SUFFIXES:
        raise UploadError("Only PDF, Markdown (.md) and text (.txt) files are accepted.")
    return name


def check_bytes(filename: str, data: bytes) -> None:
    """Refuse empty or oversized files, fake PDFs, and text files that are not text."""
    if not data:
        raise UploadError("The file is empty.")
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise UploadError(f"The file is over {config.MAX_UPLOAD_MB} MB.")
    if filename.lower().endswith(".pdf"):
        if not data.startswith(b"%PDF"):  # every real PDF starts with these 4 bytes
            raise UploadError("This file is not a real PDF.")
    else:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise UploadError("This text file is not UTF-8 text.") from error


def pdf_pages(path: Path) -> list[str]:
    """The text of every page. pypdfium2 is already installed (Docling's PDF backend)."""
    import pypdfium2

    document = pypdfium2.PdfDocument(str(path))
    try:
        return [document[number].get_textpage().get_text_range() for number in range(len(document))]
    finally:
        document.close()


def count_pages(path: Path) -> int:
    """Pages of a PDF (milliseconds, read BEFORE any slow work); text files count as 1."""
    if path.suffix.lower() != ".pdf":
        return 1
    import pypdfium2

    document = pypdfium2.PdfDocument(str(path))
    try:
        return len(document)
    finally:
        document.close()


def read_text(path: Path) -> str:
    """Markdown-ish text of one upload. PDF pages get "# Page N" headings."""
    if path.suffix.lower() == ".pdf":
        pages = pdf_pages(path)
        # Level 1 ("# "): each page heading REPLACES the last one in heading_path. With "## "
        # every chunk got "Page 1 > Page N" (heading_path keeps one level-1 parent).
        text = "\n\n".join(f"# Page {n}\n\n{page}" for n, page in enumerate(pages, start=1))
    else:
        text = path.read_text(encoding="utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def save_upload(
    name: str, data: bytes, chat_id: str, folder: Path | None = None
) -> tuple[Path, str, str, int]:
    """Check and save one file. Returns (path on disk, display name, source, pages)."""
    filename = safe_filename(name)
    check_bytes(filename, data)
    folder = (folder or config.UPLOADS_DIR) / chat_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    path.write_bytes(data)
    try:
        pages = count_pages(path)
    except Exception as error:  # pypdfium2 raises its own error type for broken files
        path.unlink(missing_ok=True)
        raise UploadError("This PDF could not be opened.") from error
    if pages > config.MAX_UPLOAD_PAGES:
        path.unlink(missing_ok=True)
        raise UploadError(f"{pages} pages: the limit is {config.MAX_UPLOAD_PAGES} pages.")
    return path, filename, f"{SOURCE_FOLDER}/{chat_id}/{filename}", pages


def ingest_file(
    path: Path,
    source: str,
    chat_id: str,
    client: QdrantClient,
    collection: str = config.UPLOADS_COLLECTION,
) -> dict:
    """Read, chunk, embed and store one file for one chat. Returns chunks and seconds."""
    started = time.perf_counter()
    text = clean_markdown(read_text(path))
    if not re.sub(r"# Page \d+", "", text).strip():
        # A scanned PDF has pictures of text, no text: OCR is off (D-043).
        raise UploadError("No text found in this file (scanned pages are not supported).")

    chunks = fixed_token_chunks(
        text, source, config.UPLOAD_CHUNK_TOKENS, config.UPLOAD_OVERLAP_TOKENS
    )
    chunks = add_metadata(chunks, text, UPLOADS)  # licence unknown: local_only
    texts = [embedding_text(chunk) for chunk in chunks]
    vectors = embed_documents(texts)
    # BM25 length penalty from THIS file's average chunk length (a growing uploads
    # collection has no fixed corpus to average over).
    sparse_vectors = embed_sparse_documents(texts, average_length(texts))

    ensure_collection(client, collection, config.EMBEDDING_DIM, cold=True)  # A5: on disk
    delete_source(client, collection, source)  # a re-upload replaces the old version
    add_chunks(client, collection, chunks, vectors, sparse_vectors, {"chat_id": chat_id})
    return {"chunks": len(chunks), "seconds": round(time.perf_counter() - started, 1)}

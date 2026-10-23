"""Background indexing of uploaded files (D-061): the upload returns at once.

Like ChatGPT / NotebookLM: the file appears as a chip with "processing"; the UI polls the
file's status and shows "ready" (or the error) when the job is done.

Why ONE worker thread: embedding uses all CPU cores already; two files at once would
only make both slower. Why not Celery / Redis: a queue server for a one-laptop demo. The
cost: a job in progress is lost if the API restarts (its file then stays "processing").
"""

import logging
from concurrent.futures import Future, ThreadPoolExecutor

from qdrant_client import QdrantClient

from docpilot.chat import store
from docpilot.ingestion.uploads import UploadError, ingest_file

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="indexer")


def index_file(file: dict, path, client: QdrantClient) -> None:
    """The job: index one file, then record "ready" or "failed" with a safe message."""
    try:
        result = ingest_file(path, file["source"], file["chat_id"], client)
        store.update_file(
            file["id"], status="ready", chunks=result["chunks"], seconds=result["seconds"]
        )
        logger.warning("indexed %s: %d chunks", file["source"], result["chunks"])
    except UploadError as error:
        store.update_file(file["id"], status="failed", error=str(error))
    except Exception:  # never let a crash leave the chip spinning forever
        logger.exception("indexing failed: %s", file["source"])
        store.update_file(file["id"], status="failed", error="Indexing failed on the server.")


def submit(file: dict, path, client: QdrantClient) -> Future:
    """Queue the job and return immediately."""
    return executor.submit(index_file, file, path, client)

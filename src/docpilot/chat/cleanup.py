"""Delete old demo chats (Phase 7 A6, D-063): a public demo must not fill the disk forever.

Real-life example: a shop cleans the tables every night; things left for a week go.

- delete_everything(): one chat's rows, uploaded files and vectors. The "delete chat"
  button uses it too, so the button and the cleanup can never drift apart.
- start(): a background thread that, every hour, deletes chats with no activity for
  CHAT_IDLE_DAYS (7). Public mode only: on the laptop my chats stay.

Why a thread and not cron: one process, nothing to install. Why not Celery beat: a broker
to run (Stage D).
"""

import logging
import shutil
import threading
from datetime import UTC, datetime, timedelta

from qdrant_client import QdrantClient

from docpilot import config
from docpilot.chat import store
from docpilot.store.qdrant_store import delete_where

logger = logging.getLogger(__name__)


def delete_everything(chat_id: str, qdrant: QdrantClient) -> None:
    """Vectors first, then files, then rows: if a step fails, the row is still there and
    the next cleanup (or click) tries again. Rows first would leave orphan vectors."""
    delete_where(qdrant, config.UPLOADS_COLLECTION, "chat_id", chat_id)
    shutil.rmtree(config.UPLOADS_DIR / chat_id, ignore_errors=True)
    store.delete_chat(chat_id)


def cleanup_once(qdrant: QdrantClient, now: datetime | None = None) -> int:
    """Delete every chat idle for more than CHAT_IDLE_DAYS; returns how many."""
    cutoff = (now or datetime.now(UTC)) - timedelta(days=config.CHAT_IDLE_DAYS)
    old = store.idle_chats(cutoff.isoformat(timespec="seconds"))
    for chat_id in old:
        delete_everything(chat_id, qdrant)
    if old:
        logger.warning(
            "cleanup: deleted %d chats idle for over %d days", len(old), config.CHAT_IDLE_DAYS
        )
    return len(old)


def start(qdrant: QdrantClient) -> threading.Event | None:
    """Start the hourly cleanup (public mode only). Set the returned event to stop it."""
    if not config.PUBLIC_MODE:
        return None
    stop = threading.Event()

    def loop() -> None:
        # Event.wait(seconds) = sleep that wakes up at once when stop is set (shutdown).
        while not stop.is_set():
            try:
                cleanup_once(qdrant)
            except Exception:  # a failed round must not kill the thread: try next hour
                logger.exception("cleanup round failed")
            stop.wait(config.CLEANUP_EVERY_SECONDS)

    threading.Thread(target=loop, name="chat-cleanup", daemon=True).start()
    return stop

"""A label on every collection: how it was built (step 2.6).

Why: one Qdrant collection per strategy and size. Without a label, an eval can only guess
the settings from config.py, and a "recursive 400" run would be recorded as "fixed 800".
02_ingest.py writes the label; the evals read it.
"""

import json
from pathlib import Path

from docpilot import config


def manifest_path(collection: str, folder: Path = config.MANIFEST_DIR) -> Path:
    return folder / f"{collection}.json"


def save_manifest(collection: str, settings: dict, folder: Path = config.MANIFEST_DIR) -> Path:
    """Write the build settings of `collection`; overwrites the old label on re-ingest."""
    path = manifest_path(collection, folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return path


def load_manifest(collection: str, folder: Path = config.MANIFEST_DIR) -> dict | None:
    """The build settings, or None for a collection built before manifests existed."""
    path = manifest_path(collection, folder)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

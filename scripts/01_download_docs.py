"""Download four FastAPI tutorial pages (raw Markdown) into data/docs/fastapi/, plus the
code files they include with {* ... *} markers into data/code/fastapi/ (step 2.3).

Run: python scripts/01_download_docs.py

The docs are MIT-licensed (checked 2026-10-12) but stay out of git (data/docs/ and
data/code/ are gitignored): this script recreates them on any machine.
"""

import urllib.request

from docpilot import config
from docpilot.ingestion.includes import find_include_paths
from docpilot.ingestion.sources import SOURCES

# Pinned to one commit, not "master": if FastAPI edits a page tomorrow, our chunks and
# eval numbers must not change under us. Latest commit touching docs/en/docs/tutorial
# on 2026-10-12 (committed 2026-07-29). Stored once, in the source register (step 2.5).
FASTAPI_COMMIT = SOURCES["fastapi"].version
REPO_URL = f"https://raw.githubusercontent.com/fastapi/fastapi/{FASTAPI_COMMIT}"
BASE_URL = f"{REPO_URL}/docs/en/docs/tutorial"
PAGES = ["first-steps", "path-params", "query-params", "body"]


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "docpilot-learning-project"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def save(path, content: bytes) -> None:
    """write_bytes, not write_text: on Windows write_text turns newlines into CRLF, which
    changes character counts, so chunks would differ between Windows and Linux CI."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def main() -> None:
    target = config.DOCS_DIR / "fastapi"
    include_paths: list[str] = []
    for page in PAGES:
        content = download(f"{BASE_URL}/{page}.md")
        path = target / f"{page}.md"
        save(path, content)
        print(f"saved {path.relative_to(config.PROJECT_ROOT).as_posix()}  ({len(content)} bytes)")
        include_paths += find_include_paths(content.decode("utf-8"))
    print(f"done: {len(PAGES)} pages from commit {FASTAPI_COMMIT[:7]}")

    # Step 2.3: the code the pages point to, from the SAME commit (docs and code must match).
    code_root = config.CODE_DIR / "fastapi"
    unique_paths = list(dict.fromkeys(include_paths))
    for relative in unique_paths:
        save(code_root / relative, download(f"{REPO_URL}/{relative}"))
    shown = code_root.relative_to(config.PROJECT_ROOT).as_posix()
    print(f"done: {len(unique_paths)} included code files -> {shown}")


if __name__ == "__main__":
    main()

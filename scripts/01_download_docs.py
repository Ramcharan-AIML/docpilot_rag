"""Download four FastAPI tutorial pages (raw Markdown) into data/docs/fastapi/.

Run: python scripts/01_download_docs.py

The docs are MIT-licensed (checked 2026-10-12) but stay out of git (data/docs/ is
gitignored): this script recreates them on any machine.
"""

import urllib.request

from docpilot import config

# Pinned to one commit, not "master": if FastAPI edits a page tomorrow, our chunks and
# eval numbers must not change under us. Latest commit touching docs/en/docs/tutorial
# on 2026-10-12 (committed 2026-07-29).
FASTAPI_COMMIT = "d62354434b2e508fe89024213b220ca8e67dea5e"
BASE_URL = (
    f"https://raw.githubusercontent.com/fastapi/fastapi/{FASTAPI_COMMIT}/docs/en/docs/tutorial"
)
PAGES = ["first-steps", "path-params", "query-params", "body"]


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "docpilot-learning-project"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def main() -> None:
    target = config.DOCS_DIR / "fastapi"
    target.mkdir(parents=True, exist_ok=True)
    for page in PAGES:
        content = download(f"{BASE_URL}/{page}.md")
        path = target / f"{page}.md"
        # write_bytes, not write_text: on Windows write_text turns "\n" into "\r\n", which
        # changes character counts, so chunks would differ between Windows and Linux CI.
        path.write_bytes(content)
        print(f"saved {path.relative_to(config.PROJECT_ROOT).as_posix()}  ({len(content)} bytes)")
    print(f"done: {len(PAGES)} pages from commit {FASTAPI_COMMIT[:7]}")


if __name__ == "__main__":
    main()

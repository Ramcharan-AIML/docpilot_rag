"""Download the whole corpus at pinned versions (register: ingestion/sources.py, D-030).

Run: python scripts/01_download_docs.py      then: python scripts/make_notes_docx.py

- docs:      FastAPI (4 pages + included code, steps 1a/2.3), Pydantic (3), Docker (5)
- learning:  Chain-of-Thought PDF (2.7, D-044), 3 Wikipedia articles (2.8)
- interview: the learner's own notes, copied from docs/interview/ (2.8)

Everything lands in data/docs/ and data/code/, which are gitignored: this script recreates
them on any machine. Pinned commits / versions / revisions mean a page edited upstream
tomorrow can never change our chunks or golden snippets under us.
"""

import hashlib
import json
import re
import shutil
import ssl
import urllib.parse
import urllib.request

import certifi

from docpilot import config
from docpilot.ingestion.includes import find_include_paths
from docpilot.ingestion.sources import SOURCES

FASTAPI_PAGES = ["first-steps", "path-params", "query-params", "body"]
PYDANTIC_PAGES = ["config", "strict_mode", "alias"]
DOCKER_PAGES = [
    "the-basics/what-is-a-container",
    "the-basics/what-is-an-image",
    "building-images/writing-a-dockerfile",
    "running-containers/publishing-ports",
    "running-containers/persisting-container-data",
]
# Step 2.7: one pinned arXiv version; the hash proves we got exactly the file we checked.
PDF_URL = "https://arxiv.org/pdf/2201.11903v6"
PDF_FILE = config.DOCS_DIR / "cot" / "cot_2201.11903v6.pdf"
PDF_SHA256 = "7d9f878c23b460e4566aa4ec9201b1abfb3b8faefb2b1356e411cb90fef72a12"
# Step 2.8: Wikipedia's plain-text API serves only the LATEST revision, so we pin the
# revision id and stop if the article changed (the golden snippets must be re-checked).
WIKIPEDIA_REVISIONS = {
    "Retrieval-augmented generation": 1381095247,
    "Word embedding": 1374850731,
    "Evaluation measures (information retrieval)": 1375531235,
}
WIKI_HEADING = re.compile(r"^(={2,6})\s*(.*?)\s*\1$")  # "== Process ==" -> level 2
WIKI_SKIP = {"See also", "References", "External links", "Further reading", "Notes"}
MATH_START = r"{\displaystyle"  # how a formula's LaTeX line starts in the extract
INTERVIEW_FILES = ["phase_0_interview.md", "phase_2_interview.md", "phase_3_interview.md"]

# certifi's CA list, not Windows': Python's default store here holds an expired root, and
# Wikipedia's certificate failed with "certificate has expired" (checked 2026-10-20).
TLS = ssl.create_default_context(cafile=certifi.where())


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "docpilot-learning-project"})
    with urllib.request.urlopen(request, timeout=30, context=TLS) as response:
        return response.read()


def save(path, content: bytes) -> None:
    """write_bytes, not write_text: on Windows write_text turns newlines into CRLF, which
    changes character counts, so chunks would differ between Windows and Linux CI."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    print(f"  saved {path.relative_to(config.PROJECT_ROOT).as_posix()}  ({len(content)} bytes)")


def github_pages(repo: str, folder: str, pages: list[str], name: str) -> list[str]:
    """Raw Markdown pages from one pinned commit -> data/docs/<name>/<last part>.md."""
    base = f"https://raw.githubusercontent.com/{repo}/{SOURCES[name].version}/{folder}"
    texts = []
    for page in pages:
        content = download(f"{base}/{page}.md")
        save(config.DOCS_DIR / name / f"{page.split('/')[-1]}.md", content)
        texts.append(content.decode("utf-8"))
    return texts


def fastapi_code(texts: list[str]) -> None:
    """Step 2.3: the code the pages point to, from the SAME commit (docs and code match)."""
    repo = f"https://raw.githubusercontent.com/fastapi/fastapi/{SOURCES['fastapi'].version}"
    paths = list(dict.fromkeys(path for text in texts for path in find_include_paths(text)))
    for relative in paths:
        save(config.CODE_DIR / "fastapi" / relative, download(f"{repo}/{relative}"))


def wiki_to_markdown(title: str, extract: str) -> str:
    """Plain-text extract -> Markdown: "== X ==" becomes "## X"; empty link sections dropped."""
    lines, skipping = [f"# {title}", ""], False
    for line in extract.splitlines():
        heading = WIKI_HEADING.match(line.strip())
        if heading:
            skipping = heading.group(2) in WIKI_SKIP
            if not skipping:
                lines += ["", f"{'#' * len(heading.group(1))} {heading.group(2)}", ""]
        elif skipping:
            continue
        elif line.strip().startswith(MATH_START):
            # A formula arrives twice: ~60 indented lines of loose symbols, then one LaTeX
            # line. Keep only the LaTeX, as $...$ (readable, and far fewer tokens).
            lines.append("$" + line.strip()[len(MATH_START) : -1].strip() + "$")
        elif line[:1].isspace():
            continue  # the loose symbols of a formula (prose lines are never indented)
        else:
            lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"


def wikipedia_articles() -> None:
    for title, pinned in WIKIPEDIA_REVISIONS.items():
        query = urllib.parse.urlencode(
            {
                "action": "query",
                "format": "json",
                "formatversion": 2,
                "titles": title,
                "prop": "extracts|revisions",
                "explaintext": 1,
                "exsectionformat": "wiki",
                "rvprop": "ids",
            }
        )
        page = json.loads(download(f"https://en.wikipedia.org/w/api.php?{query}"))
        page = page["query"]["pages"][0]
        if page["revisions"][0]["revid"] != pinned:
            raise RuntimeError(
                f"Wikipedia '{title}' changed: revision {page['revisions'][0]['revid']}, "
                f"pinned {pinned}. Re-check its golden snippets, then update the pin."
            )
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        markdown = wiki_to_markdown(title, page["extract"])
        save(config.DOCS_DIR / "wikipedia" / f"{slug}.md", markdown.encode("utf-8"))


def cot_pdf() -> None:
    pdf = download(PDF_URL)
    if hashlib.sha256(pdf).hexdigest() != PDF_SHA256:
        # A different file would silently change chunks and golden snippets: stop.
        raise RuntimeError(f"{PDF_URL} changed: sha256 differs from the pinned one")
    save(PDF_FILE, pdf)


def interview_notes() -> None:
    """The learner's own notes: copied as they are (the Word file is built separately)."""
    for name in INTERVIEW_FILES:
        source = config.PROJECT_ROOT / "docs" / "interview" / name
        target = config.DOCS_DIR / "interview" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        print(f"  copied docs/interview/{name}")


def main() -> None:
    print("fastapi:")
    folder = "docs/en/docs/tutorial"
    fastapi_code(github_pages("fastapi/fastapi", folder, FASTAPI_PAGES, "fastapi"))
    print("pydantic:")
    github_pages("pydantic/pydantic", "docs/concepts", PYDANTIC_PAGES, "pydantic")
    print("docker:")
    folder = "content/get-started/docker-concepts"
    github_pages("docker/docs", folder, DOCKER_PAGES, "docker")
    print("cot:")
    cot_pdf()
    print("wikipedia:")
    wikipedia_articles()
    print("interview:")
    interview_notes()
    print("done. Word notes: python scripts/make_notes_docx.py")


if __name__ == "__main__":
    main()

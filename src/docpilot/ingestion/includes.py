"""Replace FastAPI include markers with the code they point to (step 2.3).

The pages say  {* ../../docs_src/first_steps/tutorial001_py310.py hl[6] *}  instead of
showing the code; the code lives in separate files. Without this step, a question like
"show me a minimal app" finds the marker but no code (failure log Q1, Q7; abstention q-007).
"""

import re
from pathlib import Path

# {* path *} and {* path hl[3] *}: the path is the first word, options after it are ignored
# (hl[...] only highlights lines on the website).
INCLUDE_MARKER = re.compile(r"\{\*\s*(?P<path>\S+)[^*]*\*\}")
# Code fence language by file type; anything else gets a plain fence.
FENCE_LANGUAGES = {".py": "python", ".json": "json", ".toml": "toml", ".sh": "bash"}


def marker_path(raw_path: str) -> str:
    """'../../docs_src/x/a.py' -> 'docs_src/x/a.py'.

    The '../../' is relative to the docs folder in the FastAPI repo (docs/en/); the files
    really live at the repo root (checked 2026-10-17: docs_src/... 200, docs/en/docs_src 404).
    """
    return raw_path.replace("../../", "", 1)


def find_include_paths(text: str) -> list[str]:
    """Every code file a page includes, without duplicates, in order of first use."""
    return list(dict.fromkeys(marker_path(m.group("path")) for m in INCLUDE_MARKER.finditer(text)))


def resolve_includes(text: str, code_root: Path) -> tuple[str, int, list[str]]:
    """Return (new_text, resolved_count, missing_paths).

    Missing files are reported, not hidden: the marker stays in the text so a failure
    is visible in the chunks too.
    """
    missing: list[str] = []
    resolved = 0
    if not code_root.is_dir():
        # Only sources with a code folder (FastAPI) have real includes. The learner's Word
        # notes QUOTE a marker as an example; resolving it reported a false "missing" (fix A).
        return text, resolved, missing

    def replace(match: re.Match) -> str:
        nonlocal resolved
        relative = marker_path(match.group("path"))
        code_file = code_root / relative
        if not code_file.is_file():
            missing.append(relative)
            return match.group(0)  # keep the marker so we can see it failed
        resolved += 1
        code = code_file.read_text(encoding="utf-8").rstrip("\n")
        language = FENCE_LANGUAGES.get(code_file.suffix, "")
        return f"```{language}\n{code}\n```"

    return INCLUDE_MARKER.sub(replace, text), resolved, missing

"""List tracked text files over 500 lines (Rule 1, D-012). Exit code 1 if any.

Run: python scripts/check_file_lengths.py   (CI runs it on every pull request)
Long files are split: Markdown continues in 2_<name>.md, Python by responsibility.
"""

import subprocess
import sys
from pathlib import Path

MAX_LINES = 500
# D-012: the project documentation stays one file unless the learner asks to split it.
ALLOWED = {"docs/PROJECT_DOCUMENTATION.md"}
TEXT_SUFFIXES = {".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".json", ".jsonl", ".cfg"}


def tracked_files() -> list[str]:
    """Files git knows about: untracked scratch files and .venv are never checked."""
    output = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
    return output.stdout.splitlines()


def too_long(paths: list[str]) -> list[tuple[str, int]]:
    """(path, line count) for every text file over MAX_LINES that is not allowed."""
    problems = []
    for path in paths:
        if path in ALLOWED or Path(path).suffix not in TEXT_SUFFIXES:
            continue
        with open(path, encoding="utf-8", errors="replace") as file:
            count = sum(1 for _ in file)
        if count > MAX_LINES:
            problems.append((path, count))
    return problems


def main() -> None:
    problems = too_long(tracked_files())
    for path, count in problems:
        print(f"{path}: {count} lines (max {MAX_LINES})")
    if problems:
        sys.exit(f"FAILED: {len(problems)} file(s) over {MAX_LINES} lines; split them")
    print(f"OK: no tracked text file over {MAX_LINES} lines")


if __name__ == "__main__":
    main()

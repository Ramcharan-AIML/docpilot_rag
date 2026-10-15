"""Remove HTML noise from Markdown before chunking (step 2.2). Code blocks stay exact.

Why: tags like <font color="#4E9A06"> mean nothing to a reader but still change the
embedding of a chunk (failure-log Q7). What we found in the 4 FastAPI pages (2026-10-15):
114 tags inside ```console blocks (a coloured terminal screenshot) and 30 in normal text
(<dfn>, <abbr>, <img>, <div>, <code>); none inside python/JSON/TOML blocks.
"""

import html
import re

# Only these tag names are removed; the words BETWEEN the tags are kept
# ("<dfn title='...'>conversion</dfn>" -> "conversion"). A fixed list instead of "any <...>"
# so that Markdown autolinks like <https://...> and text such as "List<int>" survive.
NOISE_TAGS = ("span", "div", "font", "img", "br", "b", "i", "u", "dfn", "abbr", "code")
HTML_TAG = re.compile(r"</?(?:" + "|".join(NOISE_TAGS) + r")\b[^>]*>", re.IGNORECASE)
FENCE = "```"
# Fences whose content is a rendered terminal picture, not code: cleaned like prose.
# (The plan's version skipped ALL fences, which left 114 of the 144 tags in place.)
TERMINAL_FENCES = {"console"}


def fence_language(line: str) -> str:
    """'```console' -> 'console', '```' -> ''. Options after the name are ignored."""
    rest = line.strip()[len(FENCE) :].strip()
    return rest.split()[0].lower() if rest else ""


def clean_markdown(text: str) -> str:
    """Strip noise tags from prose and terminal blocks; leave every other code block exact."""
    cleaned_lines = []
    inside_code = False
    keep_exact = False  # True inside a real code block (python, JSON, TOML, plain ...)
    for line in text.splitlines():
        if line.strip().startswith(FENCE):
            if not inside_code:  # opening fence: decide how to treat the block
                keep_exact = fence_language(line) not in TERMINAL_FENCES
            inside_code = not inside_code
            cleaned_lines.append(line)
            continue
        if inside_code and keep_exact:
            cleaned_lines.append(line)  # never edit code: it must stay exact
        elif inside_code:
            # terminal picture: drop colour tags, turn &apos; back into '
            cleaned_lines.append(html.unescape(HTML_TAG.sub("", line)))
        else:
            cleaned_lines.append(HTML_TAG.sub("", line))
    # splitlines() drops the final newline; put it back so file endings do not change
    return "\n".join(cleaned_lines) + ("\n" if text.endswith("\n") else "")

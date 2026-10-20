"""Remove HTML noise from Markdown before chunking (step 2.2). Code blocks stay exact.

Step 2.8 (Docker docs, built with the Hugo site generator): the YAML "front matter" block
at the top becomes a "# Title" line (the page has no other title), and Hugo shortcodes
like {{< youtube-embed ... >}} are removed; a tab keeps its name ("Using the CLI:").

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
FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)  # only at the very start
FRONT_MATTER_TITLE = re.compile(r"^title:\s*(.+?)\s*$", re.MULTILINE)
SHORTCODE = re.compile(r"\{\{[<%]\s*(/?)([\w-]+)([^}]*?)[>%]\}\}")  # {{< name args >}}
TAB_NAME = re.compile(r'name="([^"]+)"')
DASH_RUN = re.compile(r"-{4,}")  # Markdown needs only 3 dashes per separator cell
SPACE_RUN = re.compile(r" {2,}")


def front_matter_to_title(text: str) -> str:
    """A '---' block with 'title: What is a container?' at the top -> '# What is a container?'."""
    match = FRONT_MATTER.match(text)
    if match is None:
        return text
    title = FRONT_MATTER_TITLE.search(match.group(1))
    if title is None:
        return text[match.end() :]
    quotes = "\"'"  # YAML titles may be quoted: title: "Docker Compose"
    return f"# {title.group(1).strip(quotes)}\n" + text[match.end() :]


def replace_shortcode(match: re.Match) -> str:
    """Keep only what a reader sees: the name of an opening tab; everything else goes."""
    closing, name, arguments = match.group(1), match.group(2), match.group(3)
    if name == "tab" and not closing and (tab := TAB_NAME.search(arguments)):
        return f"{tab.group(1)}:"
    return ""


def shrink_table_row(line: str) -> str:
    """'|-------------|  a    |' -> '|---| a |' (fix B, step 2.9).

    Docling pads PDF tables to fixed column widths: separator rows with hundreds of dashes
    (one dash = one token for bge-small) and cells full of spaces. Neither carries meaning,
    but the dashes eat the 510-token budget and make table chunks look alike.
    """
    return SPACE_RUN.sub(" ", DASH_RUN.sub("---", line))


def clean_prose(line: str) -> str:
    if line.lstrip().startswith("|"):
        line = shrink_table_row(line)
    return SHORTCODE.sub(replace_shortcode, HTML_TAG.sub("", line))


def fence_language(line: str) -> str:
    """'```console' -> 'console', '```' -> ''. Options after the name are ignored."""
    rest = line.strip()[len(FENCE) :].strip()
    return rest.split()[0].lower() if rest else ""


def clean_markdown(text: str) -> str:
    """Strip noise tags from prose and terminal blocks; leave every other code block exact."""
    text = front_matter_to_title(text)
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
            cleaned_lines.append(clean_prose(line))
    # splitlines() drops the final newline; put it back so file endings do not change
    return "\n".join(cleaned_lines) + ("\n" if text.endswith("\n") else "")

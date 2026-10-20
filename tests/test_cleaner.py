"""Tests for ingestion/cleaner.py: noise goes, words and real code stay."""

from docpilot.ingestion.cleaner import clean_markdown

PYTHON_WITH_TAG = '```python\nhtml = "<span>keep me</span>"\n```\n'


def test_tags_removed_from_prose_but_words_kept():
    text = 'A <dfn title="also known as: parsing">conversion</dfn> of <abbr>`Enum`</abbr>.\n'
    assert clean_markdown(text) == "A conversion of `Enum`.\n"


def test_image_and_div_tags_removed_entirely():
    text = '<div class="termy">\n<img src="/img/a.png">\nText\n</div>\n'
    assert clean_markdown(text) == "\n\nText\n\n"


def test_python_code_block_is_never_changed():
    assert clean_markdown(PYTHON_WITH_TAG) == PYTHON_WITH_TAG


def test_plain_and_json_fences_are_never_changed():
    text = '```\n<b>x</b>\n```\n```JSON\n{"a": "<font>y</font>"}\n```\n'
    assert clean_markdown(text) == text


def test_console_block_is_cleaned_like_a_terminal_picture():
    text = (
        "```console\n"
        '$ <font color="#4E9A06">uv run fastapi</font> dev\n'
        "<b>[</b>&apos;/home/user&apos;<b>]</b>\n"
        "```\n"
    )
    expected = "```console\n$ uv run fastapi dev\n['/home/user']\n```\n"
    assert clean_markdown(text) == expected


def test_autolinks_and_generic_brackets_survive():
    text = "See <https://fastapi.tiangolo.com> and List<int>.\n"
    assert clean_markdown(text) == text


def test_clean_text_is_unchanged():
    text = "# Title\n\nNothing to clean here.\n"
    assert clean_markdown(text) == text


def test_front_matter_becomes_the_title():
    # Docker pages (Hugo): the title exists only in the YAML block at the top.
    text = '---\ntitle: "What is a container?"\nweight: 10\naliases:\n- /old/\n---\n\nBody.\n'
    assert clean_markdown(text) == "# What is a container?\n\nBody.\n"


def test_shortcodes_removed_but_tab_names_kept_and_code_untouched():
    text = (
        "{{< youtube-embed W1kWqFkiu7k >}}\n"
        '{{< tab name="Using the CLI" >}}\n'
        "Run it.\n"
        "{{< /tab >}}\n"
        '```yaml\nkey: "{{< not-a-shortcode-in-code >}}"\n```\n'
    )
    cleaned = clean_markdown(text)
    assert "youtube" not in cleaned and "{{< /tab" not in cleaned
    assert "Using the CLI:\nRun it." in cleaned
    assert '"{{< not-a-shortcode-in-code >}}"' in cleaned  # code stays exact


def test_table_padding_and_long_dashes_shrink_fix_b():
    text = "|   a     |  bb  |\n|-----------|:------:|\n```\n|-----------|\n```\n"
    cleaned = clean_markdown(text)
    assert cleaned.startswith("| a | bb |\n|---|:---:|\n")
    assert "```\n|-----------|\n```" in cleaned  # code stays exact

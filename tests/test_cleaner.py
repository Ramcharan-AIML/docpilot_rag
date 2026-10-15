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

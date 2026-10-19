"""Tests for ingestion/blocks.py: code, tables and lists stay whole; headings nest."""

from docpilot.ingestion.blocks import parse_blocks, parse_heading


def kinds(text: str) -> list[str]:
    return [block.kind for block in parse_blocks(text)]


def test_hash_comment_inside_code_is_not_a_heading():
    text = "# A\n```python\n# just a comment\n\nx = 1\n```\n"
    blocks = parse_blocks(text)
    assert [b.kind for b in blocks] == ["heading", "code"]
    assert "# just a comment\n\nx = 1" in blocks[1].text  # blank line kept inside code
    assert blocks[1].heading_path == ["A"]


def test_table_stays_one_block():
    text = "Intro.\n| name | default |\n|---|---|\n| skip | 0 |\nAfter.\n"
    blocks = parse_blocks(text)
    assert [b.kind for b in blocks] == ["paragraph", "table", "paragraph"]
    assert blocks[1].text.count("\n") == 2  # all three table rows in one block


def test_heading_path_nests_and_resets():
    text = "# A\n## B\ntext under B\n# C\ntext under C\n"
    blocks = parse_blocks(text)
    assert blocks[2].heading_path == ["A", "B"]
    assert blocks[4].heading_path == ["C"]  # a new top heading drops the old subheading


def test_heading_anchor_removed_and_hashtag_is_not_a_heading():
    assert parse_heading("## Defaults { #defaults }") == (2, "Defaults")
    assert parse_heading("#hashtag") is None


def test_list_stays_one_block_including_sub_items():
    text = (
        "FastAPI will:\n\n"
        "* Read the body.\n* Validate the data.\n    * If invalid, error.\n\n"
        "End.\n"
    )
    blocks = parse_blocks(text)
    assert [b.kind for b in blocks] == ["paragraph", "list", "paragraph"]
    assert blocks[1].text.count("\n") == 2


def test_paragraph_lines_join_and_blank_lines_split():
    assert kinds("one\ntwo\n\nthree\n") == ["paragraph", "paragraph"]


def test_unclosed_code_block_is_kept():
    blocks = parse_blocks("```python\nx = 1\n")
    assert [b.kind for b in blocks] == ["code"] and "x = 1" in blocks[0].text


def test_every_block_knows_its_exact_position():
    text = "# A\n\nFirst para\nstill first.\n\n```python\nx = 1\n\ny = 2\n```\n* item\n"
    for block in parse_blocks(text):
        if block.kind == "heading":
            assert text[block.start : block.end] == "# A"
        else:
            assert text[block.start : block.end] == block.text

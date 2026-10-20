"""Tests for chunkers/qa_pairs.py: a question and its answer are never separated."""

from docpilot.ingestion.chunkers.qa_pairs import find_pairs, qa_pair_chunks

NOTES = (
    "# Interview Notes\n\nIntro text.\n\n"
    "### Q1. What is RAG?\n\nRetrieval plus generation.\n\n"
    "### Q2. Why evals?\n\nTo measure, not guess.\n\n"
    "## Other topics\n\nNot part of Q2.\n"
)


def test_each_pair_is_one_chunk_and_text_outside_is_separate():
    chunks = qa_pair_chunks(NOTES, "i.md", chunk_tokens=400)
    texts = [chunk.text for chunk in chunks]
    assert "### Q1. What is RAG?\n\nRetrieval plus generation." in texts
    assert "### Q2. Why evals?\n\nTo measure, not guess." in texts
    assert any(text.startswith("# Interview Notes") for text in texts)
    assert any(text.startswith("## Other topics") for text in texts)  # higher heading ends Q2


def test_bold_question_format_is_found():
    text = "**Q:** What is a token?\nA piece of a word.\n\n**Q:** What is 512?\nThe limit.\n"
    questions = [question for _, question in find_pairs(text) if question]
    assert questions == ["**Q:** What is a token?", "**Q:** What is 512?"]


def test_long_answer_pieces_carry_the_question_as_prefix():
    answer = " ".join(f"Point {i} about vector databases." for i in range(60))
    text = f"### Q7. Explain vector databases.\n\n{answer}\n"
    chunks = qa_pair_chunks(text, "i.md", chunk_tokens=60)
    assert len(chunks) > 1
    assert chunks[0].text.startswith("### Q7.") and chunks[0].prefix == ""
    assert all(c.prefix == "### Q7. Explain vector databases.\n\n" for c in chunks[1:])

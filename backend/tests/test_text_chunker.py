from app.services.text_chunker import chunk_text, split_into_paragraphs


def test_split_into_paragraphs_removes_empty_parts():
    text = " First paragraph. \n\n   \n\nSecond paragraph.  "

    result = split_into_paragraphs(text)

    assert result == ["First paragraph.", "Second paragraph."]


def test_chunk_text_merges_short_paragraphs_within_chunk_size():
    text = "Alpha.\n\nBeta.\n\nGamma."

    result = chunk_text(text, chunk_size=20, overlap=2)

    assert result == ["Alpha.\n\nBeta.", "Gamma."]


def test_chunk_text_validates_overlap_and_chunk_size():
    try:
        chunk_text("abc", chunk_size=0, overlap=0)
        assert False, "Expected ValueError for chunk_size <= 0"
    except ValueError as exc:
        assert "chunk_size" in str(exc)

    try:
        chunk_text("abc", chunk_size=10, overlap=10)
        assert False, "Expected ValueError for overlap >= chunk_size"
    except ValueError as exc:
        assert "overlap" in str(exc)

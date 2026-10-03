from superai_review.documents.isolation import ProcessExtractionRunner
from superai_review.documents.types import DocumentMime


def test_text_extraction_runs_in_isolated_process() -> None:
    result = ProcessExtractionRunner(
        timeout_seconds=10,
        pdf_text_min_chars_per_page=24,
    ).run(b"isolated text", DocumentMime.TEXT)

    assert result.segments[0].text == "isolated text"
    assert result.content_type is DocumentMime.TEXT

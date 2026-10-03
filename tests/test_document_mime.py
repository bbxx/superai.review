from io import BytesIO
from zipfile import ZipFile

import pytest
from docx import Document as DocxDocument

from superai_review.documents.errors import (
    DeclaredTypeMismatchError,
    InvalidFilenameError,
    UnsafeDocumentError,
)
from superai_review.documents.mime import detect_mime
from superai_review.documents.types import DocumentMime


def docx_bytes() -> bytes:
    document = DocxDocument()
    document.add_paragraph("Hello")
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def test_detects_supported_magic_types() -> None:
    assert detect_mime(b"%PDF-1.7\n", "a.pdf", "application/pdf") is DocumentMime.PDF
    assert (
        detect_mime(b"\x89PNG\r\n\x1a\nrest", "a.png", "image/png")
        is DocumentMime.PNG
    )
    assert detect_mime(b"\xff\xd8\xffrest", "a.jpg", "image/jpeg") is DocumentMime.JPEG
    assert detect_mime(docx_bytes(), "a.docx", None) is DocumentMime.DOCX
    assert detect_mime(b"# heading", "a.md", "text/markdown") is DocumentMime.MARKDOWN
    assert detect_mime(b"plain text", "a.txt", "text/plain") is DocumentMime.TEXT


def test_declared_binary_type_must_match_content() -> None:
    with pytest.raises(DeclaredTypeMismatchError):
        detect_mime(b"this is actually text", "fake.pdf", "application/pdf")


def test_path_traversal_filename_is_rejected() -> None:
    with pytest.raises(InvalidFilenameError):
        detect_mime(b"%PDF-1.7\n", "../secret.pdf", "application/pdf")


def test_pdf_active_content_is_rejected_before_parser() -> None:
    with pytest.raises(UnsafeDocumentError):
        detect_mime(
            b"%PDF-1.7\n1 0 obj << /JavaScript 2 0 R >>",
            "active.pdf",
            "application/pdf",
        )


def test_macro_docx_is_rejected() -> None:
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<w:document/>")
        archive.writestr("word/vbaProject.bin", b"macro")

    with pytest.raises(UnsafeDocumentError):
        detect_mime(output.getvalue(), "macro.docx", None)

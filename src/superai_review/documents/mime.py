from io import BytesIO
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

from superai_review.documents.errors import (
    DeclaredTypeMismatchError,
    InvalidFilenameError,
    UnsafeDocumentError,
    UnsupportedDocumentError,
)
from superai_review.documents.types import DocumentMime

_GENERIC_DECLARED_TYPES = {"", "application/octet-stream"}
_DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
_PDF_ACTIVE_MARKERS = (b"/JavaScript", b"/Launch", b"/EmbeddedFile")


def validate_filename(filename: str) -> None:
    if (
        not filename
        or len(filename) > 255
        or "\x00" in filename
        or "/" in filename
        or "\\" in filename
        or filename in {".", ".."}
        or PurePosixPath(filename).is_absolute()
    ):
        raise InvalidFilenameError("unsafe upload filename")


def _is_safe_zip_member(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts


def _detect_docx(data: bytes) -> bool:
    try:
        with ZipFile(BytesIO(data)) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > 5000:
                raise UnsafeDocumentError("unsafe DOCX archive")
            if any(not _is_safe_zip_member(info.filename) for info in infos):
                raise UnsafeDocumentError("unsafe DOCX member path")
            if sum(info.file_size for info in infos) > 64 * 1024 * 1024:
                raise UnsafeDocumentError("DOCX expands beyond safety limit")
            names = {info.filename for info in infos}
            if "word/vbaProject.bin" in names:
                raise UnsafeDocumentError("macro-enabled DOCX is not supported")
            return "[Content_Types].xml" in names and "word/document.xml" in names
    except BadZipFile:
        return False


def _text_mime(data: bytes, filename: str, declared: str) -> DocumentMime | None:
    if b"\x00" in data:
        return None
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return None

    lower_name = filename.casefold()
    if declared == DocumentMime.MARKDOWN.value or lower_name.endswith((".md", ".markdown")):
        return DocumentMime.MARKDOWN
    return DocumentMime.TEXT


def detect_mime(data: bytes, filename: str, declared_content_type: str | None) -> DocumentMime:
    validate_filename(filename)
    declared = (declared_content_type or "").split(";", 1)[0].strip().casefold()

    if data.startswith(b"%PDF-"):
        if any(marker in data for marker in _PDF_ACTIVE_MARKERS):
            raise UnsafeDocumentError("active PDF content is not supported")
        detected = DocumentMime.PDF
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        detected = DocumentMime.PNG
    elif data.startswith(b"\xff\xd8\xff"):
        detected = DocumentMime.JPEG
    elif data.startswith(b"PK") and _detect_docx(data):
        detected = DocumentMime.DOCX
    else:
        text_type = _text_mime(data, filename, declared)
        if text_type is None:
            raise UnsupportedDocumentError("unsupported or unrecognized document")
        detected = text_type

    if declared not in _GENERIC_DECLARED_TYPES:
        equivalent_text = {
            (DocumentMime.TEXT.value, DocumentMime.MARKDOWN.value),
            (DocumentMime.MARKDOWN.value, DocumentMime.TEXT.value),
        }
        if declared != detected.value and (declared, detected.value) not in equivalent_text:
            raise DeclaredTypeMismatchError(
                f"declared content type {declared!r} does not match detected {detected.value!r}"
            )
    return detected

import multiprocessing
from queue import Empty
from typing import Any, Protocol

from superai_review.documents.errors import (
    DocumentError,
    ExtractionFailedError,
    ExtractionTimeoutError,
    InvalidPasswordError,
    OCRUnavailableError,
    PasswordRequiredError,
)
from superai_review.documents.extractor import DocumentExtractor
from superai_review.documents.ocr import TesseractOCRService
from superai_review.documents.types import DocumentMime, ExtractedDocument

_ERROR_TYPES: dict[str, type[DocumentError]] = {
    error.__name__: error
    for error in (
        ExtractionFailedError,
        InvalidPasswordError,
        OCRUnavailableError,
        PasswordRequiredError,
    )
}


class ExtractionRunner(Protocol):
    def run(
        self,
        data: bytes,
        content_type: DocumentMime,
        password: str | None = None,
    ) -> ExtractedDocument:
        ...


def _worker(
    queue: Any,
    data: bytes,
    content_type: str,
    password: str | None,
    min_chars: int,
) -> None:
    try:
        result = DocumentExtractor(
            TesseractOCRService(),
            pdf_text_min_chars_per_page=min_chars,
        ).extract(data, DocumentMime(content_type), password)
        queue.put(("ok", result.model_dump(mode="json")))
    except DocumentError as exc:
        queue.put(("error", exc.__class__.__name__, str(exc)))


class ProcessExtractionRunner:
    """Runs untrusted document parsers in a killable child process."""

    def __init__(self, *, timeout_seconds: float, pdf_text_min_chars_per_page: int) -> None:
        self._timeout_seconds = timeout_seconds
        self._min_chars = pdf_text_min_chars_per_page

    def run(
        self,
        data: bytes,
        content_type: DocumentMime,
        password: str | None = None,
    ) -> ExtractedDocument:
        context = multiprocessing.get_context("spawn")
        queue = context.Queue(maxsize=1)
        process = context.Process(
            target=_worker,
            args=(queue, data, content_type.value, password, self._min_chars),
            daemon=True,
        )
        process.start()
        process.join(self._timeout_seconds)
        if process.is_alive():
            process.terminate()
            process.join(2)
            raise ExtractionTimeoutError("document extraction timed out")

        try:
            message = queue.get(timeout=1)
        except Empty as exc:
            raise ExtractionFailedError("isolated extractor returned no result") from exc
        finally:
            queue.close()

        if message[0] == "ok":
            return ExtractedDocument.model_validate(message[1])
        error_type = _ERROR_TYPES.get(message[1], ExtractionFailedError)
        raise error_type(message[2])


class InProcessExtractionRunner:
    """Deterministic test runner; production uses ProcessExtractionRunner."""

    def __init__(self, extractor: DocumentExtractor) -> None:
        self._extractor = extractor

    def run(
        self,
        data: bytes,
        content_type: DocumentMime,
        password: str | None = None,
    ) -> ExtractedDocument:
        return self._extractor.extract(data, content_type, password)

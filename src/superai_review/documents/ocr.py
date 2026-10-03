from io import BytesIO
from typing import Protocol

import pymupdf
import pytesseract
from PIL import Image, UnidentifiedImageError

from superai_review.documents.errors import ExtractionFailedError, OCRUnavailableError


class OCRService(Protocol):
    def image_to_text(self, data: bytes) -> str:
        ...

    def pdf_page_to_text(
        self,
        data: bytes,
        page_index: int,
        password: str | None = None,
    ) -> str:
        ...


class TesseractOCRService:
    def image_to_text(self, data: bytes) -> str:
        try:
            with Image.open(BytesIO(data)) as image:
                image.load()
                return self._run_tesseract(image)
        except UnidentifiedImageError as exc:
            raise ExtractionFailedError("invalid image") from exc

    def pdf_page_to_text(
        self,
        data: bytes,
        page_index: int,
        password: str | None = None,
    ) -> str:
        try:
            document = pymupdf.open(stream=data, filetype="pdf")
            if document.needs_pass and not document.authenticate(password or ""):
                raise ExtractionFailedError("PDF authentication failed for OCR")
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(dpi=180, alpha=False)
            with Image.open(BytesIO(pixmap.tobytes("png"))) as image:
                image.load()
                return self._run_tesseract(image)
        except OCRUnavailableError:
            raise
        except Exception as exc:
            raise ExtractionFailedError("failed to render PDF page for OCR") from exc

    @staticmethod
    def _run_tesseract(image: Image.Image) -> str:
        try:
            return pytesseract.image_to_string(image)
        except pytesseract.TesseractNotFoundError as exc:
            raise OCRUnavailableError("Tesseract runtime is not installed") from exc
